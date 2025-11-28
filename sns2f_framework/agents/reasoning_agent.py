# sns2f_framework/agents/reasoning_agent.py

import logging
import os
import json
import threading
import re
from collections import deque # <--- New Import for history buffer
from typing import Dict, Any, List

from huggingface_hub import hf_hub_download
from llama_cpp import Llama

from sns2f_framework.agents.base_agent import BaseAgent
from sns2f_framework.core.event_bus import (
    EventBus, 
    EVENT_REASONING_QUERY, 
    EVENT_REASONING_RESPONSE,
    EVENT_EXTRACT_FACTS,
    EVENT_GAP_DETECTED
)
from sns2f_framework.memory.memory_manager import MemoryManager
from sns2f_framework.config import MODEL_DIR, MODEL_REPO, MODEL_FILENAME
from sns2f_framework.reasoning.symbolic_engine import SymbolicEngine
from sns2f_framework.core.self_monitor import SelfMonitor 
from sns2f_framework.tools.code_executor import CodeExecutor
from sns2f_framework.core.trace_manager import trace_manager

log = logging.getLogger(__name__)

class ReasoningAgent(BaseAgent):
    """
    The Generative Brain of the swarm.
    V2.1: Now with Conversational Memory.
    """

    def __init__(self, name: str, event_bus: EventBus, memory_manager: MemoryManager):
        super().__init__(name, event_bus)
        self.memory_manager = memory_manager
        self.self_monitor = SelfMonitor(memory_manager)
        
        # --- NEW: Chat History Buffer ---
        # Stores the last 3 exchanges (User + AI) to maintain context
        self.chat_history = deque(maxlen=6) 
        # --------------------------------

        self.llm: Llama = None
        self._model_path = os.path.join(MODEL_DIR, MODEL_FILENAME)
        self.llm_lock = threading.Lock()
        
        self.subscribe(EVENT_REASONING_QUERY, self._on_query_received)
        self.subscribe(EVENT_EXTRACT_FACTS, self._on_extract_facts)

    def setup(self):
        self._ensure_model_exists()
        self._load_model()

    def process_step(self): pass

    def safe_generate(self, *args, **kwargs):
        if not self.llm: raise RuntimeError("LLM not loaded")
        with self.llm_lock: return self.llm(*args, **kwargs)

    def _ensure_model_exists(self):
        if not os.path.exists(self._model_path):
            os.makedirs(MODEL_DIR, exist_ok=True)
            try: hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILENAME, local_dir=MODEL_DIR, local_dir_use_symlinks=False)
            except Exception: pass

    def _load_model(self):
        try:
            self.llm = Llama(model_path=self._model_path, n_ctx=2048, verbose=False)
            log.info(f"[{self.name}] Neural Engine Online.")
        except Exception: pass

    def _on_query_received(self, query_text: str, request_id: str):
        log.info(f"[{self.name}] Thinking about: '{query_text}'")
        trace_manager.record(request_id, self.name, "Processing Query", query_text)
        
        try:
            # 1. Retrieve Context
            concepts = self.memory_manager.find_relevant_concepts(query_text, k=2, min_similarity=0.5)
            memories = self.memory_manager.find_relevant_memories(query_text, k=3, min_similarity=0.4)
            
            trace_manager.record(request_id, self.name, "Retrieval Complete", f"C:{len(concepts)} M:{len(memories)}")

            # Curiosity check
            concept_score = concepts[0][1] if concepts else 0.0
            memory_score = memories[0][1] if memories else 0.0
            peak_confidence = max(concept_score, memory_score)
            
            if peak_confidence < 0.5: 
                log.warning(f"[{self.name}] Low confidence ({peak_confidence:.2f}). Triggering Curiosity.")
                
                # FIX: Extract keyword so search doesn't fail
                search_topic = self._extract_topic(query_text)
                log.info(f"[{self.name}] Refined search topic: '{search_topic}'")
                
                trace_manager.record(request_id, self.name, "Gap Detected", f"Topic: {search_topic}")
                self.publish(EVENT_GAP_DETECTED, topic=search_topic, request_id=request_id)

            context_text = ""
            sources = set()

            # Self-Reflect
            if any(t in query_text.lower() for t in ["you", "your", "self", "turiya"]):
                context_text += f"{self.self_monitor.get_system_report()}\n\n"
                sources.add("Self-Monitor")

            # Build Context String
            if concepts:
                context_text += "--- Concepts ---\n"
                for c, _ in concepts: context_text += f"{c['name']}: {c['definition']}\n"
            if memories:
                context_text += "--- Memories ---\n"
                for m, _ in memories: 
                    context_text += f"- {m['content']}\n"
                    sources.add(json.loads(m['metadata']).get('original_source', 'unknown'))

            if not context_text: context_text = "No info."

            # --- NEW: Build Prompt with History ---
            # We reconstruct the conversation flow for the LLM
            history_text = ""
            for msg in self.chat_history:
                role = "<|user|>" if msg['role'] == 'user' else "<|assistant|>"
                history_text += f"{role}\n{msg['content']}</s>\n"

            prompt = (
                f"<|system|>\n"
                f"You are Turiya. Use the Context below to answer the user.\n"
                f"If code is needed, use ```python ... ``` blocks. Do not use input().\n"
                f"Context:\n{context_text}</s>\n"
                f"{history_text}"  # <--- Inject History Here
                f"<|user|>\n"
                f"{query_text}</s>\n"
                f"<|assistant|>\n"
            )
            # --------------------------------------
            
            # Generate
            output = self.safe_generate(prompt, max_tokens=400, stop=["</s>"], echo=False)
            response_text = output['choices'][0]['text'].strip()

            # Check for Tools
            code_blocks = re.findall(r"```python(.*?)```", response_text, re.DOTALL)
            if code_blocks:
                trace_manager.record(request_id, self.name, "Tool Usage", "Detected Python Code")
                execution_result = CodeExecutor.execute(code_blocks[-1])
                response_text += f"\n\n--- 🔧 TOOL OUTPUT ---\n{execution_result}"
                sources.add("Code Interpreter")

            if sources:
                response_text += f"\n\n(Sources: {', '.join(list(sources))})"

            # --- NEW: Update History ---
            self.chat_history.append({'role': 'user', 'content': query_text})
            # We strip the sources for history to keep it clean context
            clean_response = response_text.split('\n\n(Sources:')[0]
            self.chat_history.append({'role': 'assistant', 'content': clean_response})
            # ---------------------------

            self.publish(EVENT_REASONING_RESPONSE, request_id=request_id, response=response_text)
            
        except Exception as e:
            log.error(f"[{self.name}] Error: {e}", exc_info=True)
            self.publish(EVENT_REASONING_RESPONSE, request_id=request_id, response="Error thinking.")

    def _on_extract_facts(self, text: str, source: str):
        if not self.llm: return
        triples = SymbolicEngine.extract_triples(text, self.safe_generate)
        if triples:
            count = 0
            for (subj, pred, obj) in triples:
                res = self.memory_manager.add_symbolic_fact(subj, pred, obj, {"source": source})
                if res > 0: count += 1
            if count > 0:
                log.info(f"[{self.name}] Graph Updated: +{count} facts from {source}")
    
    def _extract_topic(self, query: str) -> str:
        """
        Uses the LLM to convert a complex question into a simple search keyword.
        NOW AWARE OF CONTEXT (History).
        """
        # Get the last few messages to provide context
        history_context = ""
        if self.chat_history:
            last_exchange = list(self.chat_history)[-2:] # Get last user/ai pair
            for msg in last_exchange:
                role = "User" if msg['role'] == 'user' else "Assistant"
                history_context += f"{role}: {msg['content']}\n"

        prompt = (
            f"Extract the main search keyword/entity from the last question.\n"
            f"Use the conversation history to resolve pronouns like 'he', 'she', 'it'.\n\n"
            f"History:\n"
            f"User: Who is Alan Turing?\n"
            f"Assistant: Alan Turing was a mathematician.\n"
            f"User: When did he die?\n"
            f"Keyword: Alan Turing death\n\n"
            f"History:\n"
            f"{history_context}"
            f"User: {query}\n"
            f"Keyword:"
        )
        
        try:
            output = self.safe_generate(prompt, max_tokens=15, stop=["\n"], echo=False)
            keyword = output['choices'][0]['text'].strip()
            return keyword if keyword else query
        except:
            return query
        
    