# sns2f_framework/agents/reasoning_agent.py

import logging
import os
import threading
import json
import re
from collections import deque
from typing import Dict, Any, List

from huggingface_hub import hf_hub_download
from llama_cpp import Llama

from sns2f_framework.agents.base_agent import BaseAgent
from sns2f_framework.core.event_bus import (
    EventBus, EVENT_REASONING_QUERY, EVENT_REASONING_RESPONSE,
    EVENT_EXTRACT_FACTS, EVENT_GAP_DETECTED
)
from sns2f_framework.memory.memory_manager import MemoryManager
from sns2f_framework.tools.code_executor import CodeExecutor
from sns2f_framework.core.trace_manager import trace_manager
from sns2f_framework.core.language_engine import LanguageEngine
from sns2f_framework.core.language_generator import LanguageGenerator
from sns2f_framework.config import MODEL_DIR, MODEL_REPO, MODEL_FILENAME
from sns2f_framework.reasoning.symbolic_engine import SymbolicEngine
from sns2f_framework.core.self_monitor import SelfMonitor 

log = logging.getLogger(__name__)

class ReasoningAgent(BaseAgent):
    """
    The Hybrid Brain (V7.0: Self-Aware).
    Records its own actions into the Knowledge Graph to build an identity.
    """

    def __init__(self, name: str, event_bus: EventBus, memory_manager: MemoryManager):
        super().__init__(name, event_bus)
        self.memory_manager = memory_manager
        
        # Engines
        self.lang_engine = LanguageEngine()
        self.lang_gen = LanguageGenerator(memory_manager) 
        self.self_monitor = SelfMonitor(memory_manager)
        
        # Context
        self.chat_history = deque(maxlen=6)

        # Neural Engine
        self.llm: Llama = None
        self._model_path = os.path.join(MODEL_DIR, MODEL_FILENAME)
        self.llm_lock = threading.Lock()
        
        self.subscribe(EVENT_REASONING_QUERY, self._on_query_received)
        self.subscribe(EVENT_EXTRACT_FACTS, self._on_extract_facts)

    def setup(self):
        log.info(f"[{self.name}] Booting Hybrid Core...")
        self._ensure_model_exists()
        self._load_model()
        
        # --- NEW: Initialize Self-Concept ---
        # We ensure "Turiya" exists as a subject in the graph
        self._update_self_model("is", "an Artificial Intelligence")
        self._update_self_model("runs on", "Local Hardware")

    def safe_generate(self, *args, **kwargs):
        if not self.llm: return None
        with self.llm_lock: return self.llm(*args, **kwargs)

    def _ensure_model_exists(self):
        if not os.path.exists(self._model_path):
            log.warning(f"[{self.name}] Downloading Neural Engine...")
            os.makedirs(MODEL_DIR, exist_ok=True)
            try: hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILENAME, local_dir=MODEL_DIR, local_dir_use_symlinks=False)
            except: pass

    def _load_model(self):
        try:
            self.llm = Llama(model_path=self._model_path, n_ctx=4096, verbose=False)
            log.info(f"[{self.name}] Neural Engine Online.")
        except: pass

    def process_step(self): pass

    def _on_query_received(self, query_text: str, request_id: str):
        log.info(f"[{self.name}] Ingesting: '{query_text}'")
        trace_manager.record(request_id, self.name, "Surface Layer", query_text)
        
        parsed = self.lang_engine.parse_query(query_text)
        intent = parsed.get("intent", "unknown")
        target = parsed.get("target", query_text)
        search_target = self._clean_target_name(target)
        
        response = ""
        tool_used = False

        # ROUTING & EXECUTION
        if intent == "action:calculate":
            try:
                expr = parsed.get('expression', target)
                expr = re.sub(r'(?i)\b(calculate|solve|compute|what is)\b', '', expr).strip("?. ")
                result = CodeExecutor.execute(f"print({expr})")
                response = f"Calculation Result:\n{result}"
                tool_used = True
                self._update_self_model("can perform", "calculation") # <--- RECORD SKILL
            except Exception as e:
                response = f"Calculation failed: {e}"

        elif intent in ["query:identity", "query:definition", "query:explanation", "unknown"]:
            facts = self._retrieve_facts(search_target)
            
            if facts:
                response = self._synthesize_with_llm(target, facts)
                self._update_self_model("knows about", target) # <--- RECORD KNOWLEDGE
            else:
                # Gap
                search_topic = target if len(target.split()) < 5 else self._extract_topic(query_text)
                self.publish(EVENT_GAP_DETECTED, topic=search_topic, request_id=request_id)
                response = self.lang_gen.generate_unknown(target)
                self._update_self_model("is learning about", target) # <--- RECORD CURIOSITY

        # --- NEW: SELF-REFLECTION CHECK ---
        # If the user asks about Turiya, we inject the "Ego" facts
        if any(t in query_text.lower() for t in ["who are you", "what are you", "tell me about yourself"]):
            self_facts = self._retrieve_facts("Turiya")
            if self_facts:
                self_story = self._synthesize_with_llm("Turiya", self_facts)
                response = f"{self_story}\n\n(Internal Stats: {self.self_monitor.get_system_report()})"
        
        # UPDATE HISTORY
        self.chat_history.append({'role': 'user', 'content': query_text})
        self.chat_history.append({'role': 'assistant', 'content': response})

        self.publish(EVENT_REASONING_RESPONSE, request_id=request_id, response=response)

    def _update_self_model(self, predicate: str, object_val: str):
        """
        Writes an autobiographical fact to the Knowledge Graph.
        (Turiya, [predicate], [object])
        """
        # We use the MemoryManager to inject the fact directly
        # Subject is always "Turiya"
        self.memory_manager.add_symbolic_fact(
            subject="Turiya",
            predicate=predicate,
            object_val=object_val,
            context={"source": "self_reflection"}
        )

    def _clean_target_name(self, name: str) -> str:
        titles = ["Lord", "Lady", "Sir", "Dr", "Doctor", "The", "Mr", "Ms", "Mrs", "Prof", "Professor"]
        clean = name
        for title in titles:
            clean = re.sub(rf"(?i)^{title}\s+", "", clean)
        return clean.strip()

    def _synthesize_with_llm(self, subject: str, facts: List[tuple]) -> str:
        if not self.llm: return self.lang_gen._realize_narrative(subject, facts)

        fact_list = "\n".join([f"- {s} {p} {o}" for s, p, o in facts[:12]])
        
        prompt = (
            f"<|system|>\n"
            f"You are Turiya, an AI. Summarize the facts below into a natural response. "
            f"If the facts are about 'Turiya', speak in the first person ('I am...'). "
            f"Only use the provided facts.\n\n"
            f"Facts about {subject}:\n{fact_list}</s>\n"
            f"<|user|>\n"
            f"Write a biography about {subject}.\n"
            f"<|assistant|>\n"
        )

        try:
            output = self.safe_generate(prompt, max_tokens=200, stop=["</s>"], echo=False)
            return output['choices'][0]['text'].strip()
        except Exception as e:
            log.error(f"LLM Synthesis failed: {e}")
            return self.lang_gen._realize_narrative(subject, facts)

    def _retrieve_facts(self, entity_name: str) -> List[tuple]:
        facts = []
        conn = self.memory_manager.ltm._get_connection()
        
        cursor = conn.execute(
            "SELECT subject, predicate, object FROM symbolic_knowledge WHERE subject LIKE ? ORDER BY LENGTH(subject) ASC LIMIT 15",
            (f"%{entity_name}%",)
        )
        rows = cursor.fetchall()
        
        if len(rows) < 3 and " " in entity_name:
            terms = entity_name.split()
            if len(terms) > 1 and len(terms[-1]) > 3:
                surname = terms[-1]
                cursor = conn.execute(
                    "SELECT subject, predicate, object FROM symbolic_knowledge WHERE subject LIKE ? ORDER BY LENGTH(subject) ASC LIMIT 10",
                    (f"%{surname}%",)
                )
                rows.extend(cursor.fetchall())

        seen = set()
        for r in rows:
            ft = (r['subject'], r['predicate'], r['object'])
            if ft not in seen and len(r['subject']) < 100:
                facts.append(ft)
                seen.add(ft)
        
        return facts

    def _on_extract_facts(self, text: str, source: str):
        triples = self.lang_engine.extract_triples_rule_based(text)
        if triples:
            count = 0
            for (s, p, o) in triples:
                res = self.memory_manager.add_symbolic_fact(s, p, o, {"source": source})
                if res > 0: count += 1
            if count > 0:
                log.info(f"[{self.name}] Graph Updated: +{count} facts")
                
    def _extract_topic(self, query: str) -> str:
        return query