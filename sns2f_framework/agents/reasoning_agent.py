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
    The Hybrid Brain (V7.1: Stable).
    Fixed data type handling between Retrieval and Generation.
    """

    def __init__(self, name: str, event_bus: EventBus, memory_manager: MemoryManager):
        super().__init__(name, event_bus)
        self.memory_manager = memory_manager
        
        self.lang_engine = LanguageEngine()
        self.lang_gen = LanguageGenerator(memory_manager) 
        self.self_monitor = SelfMonitor(memory_manager)
        
        self.chat_history = deque(maxlen=6)
        self.llm: Llama = None
        self._model_path = os.path.join(MODEL_DIR, MODEL_FILENAME)
        self.llm_lock = threading.Lock()
        
        self.subscribe(EVENT_REASONING_QUERY, self._on_query_received)
        self.subscribe(EVENT_EXTRACT_FACTS, self._on_extract_facts)

    def setup(self):
        log.info(f"[{self.name}] Booting Hybrid Core...")
        self._ensure_model_exists()
        self._load_model()
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
        import time
        log.info(f"[{self.name}] Ingesting: '{query_text}'")
        trace_manager.record(request_id, self.name, "Surface Layer", query_text)
        
        parsed = self.lang_engine.parse_query(query_text)
        intent = parsed.get("intent", "unknown")
        target = parsed.get("target", query_text)
        search_target = self._clean_target_name(target)
        
        log.info(f"[{self.name}] Intent: {intent} | Target: {target} -> Search: {search_target}")
        
        response = ""

        if intent == "action:calculate":
            try:
                expr = parsed.get('expression', target)
                expr = re.sub(r'(?i)\b(calculate|solve|compute|what is)\b', '', expr).strip("?. ")
                result = CodeExecutor.execute(f"print({expr})")
                response = f"Calculation Result:\n{result}"
                self._update_self_model("can perform", "calculation")
            except Exception as e:
                response = f"Calculation failed: {e}"

        elif intent in ["query:identity", "query:definition", "query:explanation", "unknown"]:
            # 1. Initial Check
            facts = self._retrieve_facts(search_target)
            
            # 2. If Missing, Trigger Hunt & Wait
            if not facts:
                log.info(f"[{self.name}] Gap detected for: {target}")
                search_topic = target if len(target.split()) < 5 else self._extract_topic(query_text)
                self.publish(EVENT_GAP_DETECTED, topic=search_topic, request_id=request_id)
                self._update_self_model("is learning about", target)
                
                log.info(f"[{self.name}] Waiting for learning stream...")
                for i in range(30): 
                    time.sleep(2.0)
                    facts = self._retrieve_facts(search_target)
                    if facts:
                        log.info(f"[{self.name}] Data arrived! Resume thinking.")
                        break

            if facts:
                log.info(f"[{self.name}] Retrieved {len(facts)} facts.")
                for f in facts:
                    self.memory_manager.ltm.reinforce_fact(f['id'], amount=1.0)
                
                # FIX: Pass 'facts' directly (List of Dicts), do NOT convert to tuples yet
                response = self._synthesize_with_llm(target, facts)
                self._update_self_model("knows about", target)
            else:
                response = self.lang_gen.generate_unknown(target) + " (I am currently reading sources. Please ask me again in a moment.)"

        # Self-Reflection Logic
        if any(t in query_text.lower() for t in ["who are you", "what are you", "tell me about yourself"]):
            self_facts = self._retrieve_facts("Turiya")
            if self_facts:
                self_story = self._synthesize_with_llm("Turiya", self_facts)
                response = f"{self_story}\n\n(Internal Stats: {self.self_monitor.get_system_report()})"
        
        self.chat_history.append({'role': 'user', 'content': query_text})
        self.chat_history.append({'role': 'assistant', 'content': response})

        self.publish(EVENT_REASONING_RESPONSE, request_id=request_id, response=response)

    def _update_self_model(self, predicate: str, object_val: str):
        self.memory_manager.add_symbolic_fact("Turiya", predicate, object_val, {"source": "self_reflection"})

    def _clean_target_name(self, name: str) -> str:
        titles = ["Lord", "Lady", "Sir", "Dr", "Doctor", "The", "Mr", "Ms", "Mrs", "Prof", "Professor"]
        clean = name
        for title in titles:
            clean = re.sub(rf"(?i)^{title}\s+", "", clean, flags=re.IGNORECASE)
        
        clean = re.sub(r"^(a|an|the)\s+", "", clean, flags=re.IGNORECASE)
        return clean.strip()

    def _synthesize_with_llm(self, subject: str, facts: List[Dict]) -> str:
        """
        Takes a list of Fact Dictionaries (from _retrieve_facts) and generates text.
        """
        # Fallback if LLM missing
        if not self.llm: 
            fact_tuples = [(f['s'], f['p'], f['o']) for f in facts]
            return self.lang_gen._realize_narrative(subject, fact_tuples)

        # Build prompt from Dicts
        fact_strings = []
        for f in facts[:15]:
            fact_strings.append(f"- {f['s']} {f['p']} {f['o']}")
            
        fact_list = "\n".join(fact_strings)
        
        prompt = (
            f"<|system|>\n"
            f"You are Turiya, an AI assistant. Write a detailed summary about the topic: '{subject}'.\n"
            f"Rules:\n"
            f"1. Use ONLY the provided facts.\n"
            f"2. Write in an objective, third-person encyclopedic style.\n"
            f"3. DO NOT say 'I am {subject}'. Only use 'I' if the topic is explicitly 'Turiya'.\n\n"
            f"Facts about {subject}:\n{fact_list}</s>\n"
            f"<|user|>\n"
            f"Tell me about {subject}.\n"
            f"<|assistant|>\n"
        )

        try:
            output = self.safe_generate(prompt, max_tokens=600, stop=["</s>"], echo=False)
            return output['choices'][0]['text'].strip()
        except Exception as e:
            log.error(f"LLM Synthesis failed: {e}")
            # Fallback conversion
            fact_tuples = [(f['s'], f['p'], f['o']) for f in facts]
            return self.lang_gen._realize_narrative(subject, fact_tuples)

    def _retrieve_facts(self, entity_name: str) -> List[dict]:
        facts = []
        conn = self.memory_manager.ltm._get_connection()
        
        cursor = conn.execute(
            "SELECT id, subject, predicate, object FROM symbolic_knowledge WHERE subject LIKE ? ORDER BY usage_weight DESC, LENGTH(subject) ASC LIMIT 15",
            (f"%{entity_name}%",)
        )
        rows = cursor.fetchall()
        
        if len(rows) < 3 and " " in entity_name:
            terms = entity_name.split()
            if len(terms) > 1 and len(terms[-1]) > 3:
                surname = terms[-1]
                cursor = conn.execute(
                    "SELECT id, subject, predicate, object FROM symbolic_knowledge WHERE subject LIKE ? ORDER BY usage_weight DESC, LENGTH(subject) ASC LIMIT 10",
                    (f"%{surname}%",)
                )
                rows.extend(cursor.fetchall())

        seen = set()
        for r in rows:
            ft = (r['subject'], r['predicate'], r['object'])
            if ft not in seen and len(r['subject']) < 100:
                facts.append({'id': r['id'], 's': r['subject'], 'p': r['predicate'], 'o': r['object']})
                seen.add(ft)
        
        return facts

    def _on_extract_facts(self, text: str, source: str, confidence: float = 0.5):
        if not self.llm: return
        triples = SymbolicEngine.extract_triples(text, self.safe_generate)
        
        if triples:
            count = 0
            for (s, p, o) in triples:
                is_valid = self._judge_contradiction(s, p, o, confidence)
                if is_valid:
                    res = self.memory_manager.ltm.add_fact(s, p, o, {"source": source}, confidence)
                    if res > 0: count += 1
            if count > 0:
                log.info(f"[{self.name}] Graph Updated: +{count} facts")

    def _judge_contradiction(self, subject: str, predicate: str, new_object: str, new_conf: float) -> bool:
        if not self.llm: return True
        with self.memory_manager.ltm as conn:
            rows = conn._get_connection().execute(
                "SELECT id, object, confidence FROM symbolic_knowledge WHERE subject = ? AND predicate = ?",
                (subject, predicate)
            ).fetchall()
        
        existing_conflicts = [(r['id'], r['object'], r['confidence']) for r in rows if r['object'].lower() != new_object.lower()]
        if not existing_conflicts: return True

        conflict_desc = existing_conflicts[0][1]
        old_id = existing_conflicts[0][0]
        old_conf = existing_conflicts[0][2]

        prompt = (
            f"Judge truth:\n"
            f"A: {subject} {predicate} {new_object}\n"
            f"B: {subject} {predicate} {conflict_desc}\n"
            f"Contradictory? YES/NO."
        )
        try:
            output = self.safe_generate(prompt, max_tokens=5, stop=["\n"], echo=False)
            if "yes" in output['choices'][0]['text'].strip().lower():
                if new_conf > old_conf:
                    self.memory_manager.ltm.reinforce_fact(old_id, amount=-0.2)
                    return True
                elif old_conf > 0.8 and new_conf < 0.4:
                     return False
            return True
        except: return True

    def _extract_topic(self, query: str) -> str:
        history_context = ""
        if self.chat_history:
            for msg in list(self.chat_history)[-2:]:
                role = "User" if msg['role'] == 'user' else "Assistant"
                history_context += f"{role}: {msg['content']}\n"
        prompt = f"Extract keyword.\nHistory:\n{history_context}User: {query}\nKeyword:"
        try:
            output = self.safe_generate(prompt, max_tokens=15, stop=["\n"], echo=False)
            return output['choices'][0]['text'].strip() or query
        except: return query

if __name__ == "__main__":
    print("Test via main.py")