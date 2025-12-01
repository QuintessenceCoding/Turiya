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
        import time # Ensure time is available
        
        log.info(f"[{self.name}] Ingesting: '{query_text}'")
        trace_manager.record(request_id, self.name, "Surface Layer", query_text)
        
        parsed = self.lang_engine.parse_query(query_text)
        intent = parsed.get("intent", "unknown")
        target = parsed.get("target", query_text)
        search_target = self._clean_target_name(target)
        
        log.info(f"[{self.name}] Intent: {intent} | Target: {target}")
        
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
                
                # Trigger the Perception Agent
                search_topic = target if len(target.split()) < 5 else self._extract_topic(query_text)
                self.publish(EVENT_GAP_DETECTED, topic=search_topic, request_id=request_id)
                self._update_self_model("is learning about", target)
                
                # --- THE WAIT LOOP ---
                log.info(f"[{self.name}] Waiting for learning stream...")
                for i in range(20): # Poll 10 times (20 seconds max)
                    time.sleep(2.0)
                    # Check DB again
                    facts = self._retrieve_facts(search_target)
                    if facts:
                        log.info(f"[{self.name}] Data arrived! Resume thinking.")
                        break
                # ---------------------

            # 3. Synthesize (This handles both immediate hits AND successful waits)
            if facts:
                log.info(f"[{self.name}] Retrieved {len(facts)} facts.")
                # Hebbian Reinforcement
                for f in facts:
                    self.memory_manager.ltm.reinforce_fact(f['id'], amount=1.0)
                
                # Generate Answer
                fact_tuples = [(f['s'], f['p'], f['o']) for f in facts]
                response = self._synthesize_with_llm(target, fact_tuples)
                self._update_self_model("knows about", target)
            else:
                # 4. Timeout (Still no data after waiting)
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
        """
        Removes titles and articles to improve database matching and searching.
        """
        # 1. Remove Honorifics
        titles = ["Lord", "Lady", "Sir", "Dr", "Doctor", "The", "Mr", "Ms", "Mrs", "Prof", "Professor"]
        clean = name
        for title in titles:
            # FIX: Use flags=re.IGNORECASE instead of (?i) to avoid position errors
            clean = re.sub(rf"^{title}\s+", "", clean, flags=re.IGNORECASE)
        
        # 2. Remove Leading Articles
        # Matches "A Tardigrade" -> "Tardigrade", "An Apple" -> "Apple"
        # FIX: flags=re.IGNORECASE handles capitalization safely
        clean = re.sub(r"^(a|an|the)\s+", "", clean, flags=re.IGNORECASE)
        
        return clean.strip()

    def _synthesize_with_llm(self, subject: str, facts: List[dict]) -> str:
        """
        The Editor Pattern.
        Input: List of Fact Dictionaries.
        Output: Human Paragraph.
        """
        if not self.llm: 
            # Fallback requires tuples, so convert back if needed
            fact_tuples = [(f['s'], f['p'], f['o']) for f in facts]
            return self.lang_gen._realize_narrative(subject, fact_tuples)

        # FIX: Access dictionary keys instead of unpacking tuples
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
        """
        Queries LTM using Hebbian Ranking.
        Returns dicts now: {'id': 1, 's': '...', 'p': '...', 'o': '...'}
        """
        facts = []
        conn = self.memory_manager.ltm._get_connection()
        
        # SORT BY: usage_weight DESC (Important stuff first), then Length (Specific stuff)
        query = """
            SELECT id, subject, predicate, object 
            FROM symbolic_knowledge 
            WHERE subject LIKE ? 
            ORDER BY usage_weight DESC, LENGTH(subject) ASC 
            LIMIT 15
        """
        
        cursor = conn.execute(query, (f"%{entity_name}%",))
        rows = cursor.fetchall()
        
        # ... (Partial match logic would also use the same ORDER BY) ...

        seen = set()
        for r in rows:
            # Create a unique key for deduplication
            fact_tuple = (r['subject'], r['predicate'], r['object'])
            if fact_tuple not in seen and len(r['subject']) < 100:
                # Store ID so we can reinforce later
                facts.append({
                    'id': r['id'],
                    's': r['subject'],
                    'p': r['predicate'],
                    'o': r['object']
                })
                seen.add(fact_tuple)
        
        return facts

    def _on_extract_facts(self, text: str, source: str, confidence: float = 0.5):
        """
        Extracts facts and applies the 'Soft Judge' logic.
        """
        if not self.llm: return
        triples = SymbolicEngine.extract_triples(text, self.safe_generate)
        
        if triples:
            count = 0
            for (s, p, o) in triples:
                # 1. Check for conflicts
                is_new_info = self._handle_contradiction(s, p, o, confidence)
                
                if is_new_info:
                    # 2. Add to DB with the calculated confidence
                    res = self.memory_manager.ltm.add_fact(s, p, o, {"source": source}, confidence)
                    if res > 0: count += 1
            
            if count > 0:
                log.info(f"[{self.name}] Graph Updated: +{count} facts (Conf: {confidence})")

    def _handle_contradiction(self, subject: str, predicate: str, new_object: str, new_conf: float) -> bool:
        """
        The Soft Judge.
        Returns True if we should add the new fact.
        Side Effect: Lowers confidence of conflicting facts in the DB.
        """
        # 1. Fetch existing facts with same Subject + Predicate
        with self.memory_manager.ltm as conn:
            rows = conn._get_connection().execute(
                "SELECT id, object, confidence FROM symbolic_knowledge WHERE subject = ? AND predicate = ?",
                (subject, predicate)
            ).fetchall()
        
        existing_conflicts = [(r['id'], r['object'], r['confidence']) for r in rows]
        
        # Filter out exact duplicates (case insensitive)
        existing_conflicts = [x for x in existing_conflicts if x[1].lower() != new_object.lower()]

        if not existing_conflicts:
            return True # No conflict

        # 2. LLM Arbitration
        # We only ask the LLM if the objects seem totally different
        # (Skipping simple synonyms to save compute)
        conflict_desc = existing_conflicts[0][1]
        old_id = existing_conflicts[0][0]
        old_conf = existing_conflicts[0][2]

        log.info(f"[{self.name}] ⚖️ Judge: '{subject} {predicate} {new_object}' vs '{conflict_desc}'")
        
        prompt = (
            f"<|system|>\n"
            f"You are a Logic Judge. Analyze these two statements.\n"
            f"A: {subject} {predicate} {new_object}\n"
            f"B: {subject} {predicate} {conflict_desc}\n"
            f"Are these contradictory? (e.g. Born in 1900 vs Born in 1910). Output YES or NO.\n"
            f"<|assistant|>\n"
        )
        
        try:
            output = self.safe_generate(prompt, max_tokens=5, stop=["\n"], echo=False)
            verdict = output['choices'][0]['text'].strip().lower()
            
            if "yes" in verdict:
                # CONTRADICTION DETECTED
                # We do NOT delete. We adjust confidence.
                
                if new_conf > old_conf:
                    # New fact is more trusted. Downgrade the old one.
                    log.info(f"[{self.name}] ⚖️ Verdict: New fact is stronger. Demoting old fact.")
                    self.memory_manager.ltm.reinforce_fact(old_id, amount=-0.2) # Reduce weight/confidence
                    return True
                else:
                    # Old fact is stronger. We still add the new one, but maybe warn?
                    # Or we can choose to reject the new one if the gap is huge.
                    if old_conf > 0.8 and new_conf < 0.4:
                         log.warning(f"[{self.name}] ⚖️ Verdict: REJECTED weak new fact.")
                         return False
                    return True
            else:
                # No contradiction (e.g. "Turing is Mathematician" vs "Turing is Biologist" -> Both true)
                return True
                
        except:
            return True # Fail open
                
    def _extract_topic(self, query: str) -> str:
        return query