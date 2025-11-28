# sns2f_framework/agents/reasoning_agent.py

import logging
import os
import json
import threading
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
import re # <---this for regex parsing

log = logging.getLogger(__name__)

class ReasoningAgent(BaseAgent):
    """
    The Generative Brain of the swarm.
    """

    def __init__(self, name: str, event_bus: EventBus, memory_manager: MemoryManager):
        super().__init__(name, event_bus)
        self.memory_manager = memory_manager

        # --- NEW: SELF AWARENESS ---
        self.self_monitor = SelfMonitor(memory_manager)
        # ---------------------------

        # Internal state
        self.llm: Llama = None
        self._model_path = os.path.join(MODEL_DIR, MODEL_FILENAME)
        self.llm_lock = threading.Lock()
        
        self.subscribe(EVENT_REASONING_QUERY, self._on_query_received)
        self.subscribe(EVENT_EXTRACT_FACTS, self._on_extract_facts)
        
    def setup(self):
        log.info(f"[{self.name}] Initializing Neural Engine...")
        self._ensure_model_exists()
        self._load_model()

    def process_step(self):
        pass

    # --- SAFE GENERATION METHOD ---
    def safe_generate(self, *args, **kwargs):
        """
        Thread-safe wrapper for the LLM. 
        Blocks until the brain is free.
        """
        if not self.llm:
            raise RuntimeError("LLM not loaded")
            
        with self.llm_lock:
            return self.llm(*args, **kwargs)

    def _ensure_model_exists(self):
        if not os.path.exists(self._model_path):
            log.warning(f"[{self.name}] Model not found. Downloading...")
            os.makedirs(MODEL_DIR, exist_ok=True)
            try:
                hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILENAME, local_dir=MODEL_DIR, local_dir_use_symlinks=False)
                log.info(f"[{self.name}] Download complete.")
            except Exception as e:
                log.critical(f"[{self.name}] Download failed: {e}")

    def _load_model(self):
        try:
            log.info(f"[{self.name}] Loading LLM into RAM...")
            self.llm = Llama(model_path=self._model_path, n_ctx=2048, verbose=False)
            log.info(f"[{self.name}] Neural Engine Online.")
        except Exception as e:
            log.error(f"[{self.name}] Failed to load LLM: {e}", exc_info=True)

    def _on_query_received(self, query_text: str, request_id: str):
        log.info(f"[{self.name}] Thinking about: '{query_text}'")
        try:
            # 1. Retrieve Context (Same as before)
            concepts = self.memory_manager.find_relevant_concepts(query_text, k=2, min_similarity=0.5)
            memories = self.memory_manager.find_relevant_memories(query_text, k=3, min_similarity=0.4)
            
            # (Keep your Curiosity/Self-Reflect logic here if you wish, omitted for brevity)
            
            context_text = ""
            sources = set()
            
            # ... (Build context string from concepts/memories as before) ...
            if concepts:
                context_text += "--- Concepts ---\n"
                for c, _ in concepts: context_text += f"{c['name']}: {c['definition']}\n"
            if memories:
                context_text += "--- Memories ---\n"
                for m, _ in memories: 
                    context_text += f"- {m['content']}\n"
                    sources.add(json.loads(m['metadata']).get('original_source', 'unknown'))

            # 2. PROMPT UPGRADE: Teach it to Code
            prompt = (
                f"<|system|>\n"
                f"You are Turiya. Answer the user. "
                f"If the user asks for math, logic, or data processing, WRITE A PYTHON SCRIPT inside ```python``` tags to solve it.\n"
                f"RULES FOR CODE:\n"
                f"1. DO NOT use input(). Hardcode the values from the user's question.\n"
                f"2. ALWAYS print() the final result.\n\n"
                f"Example:\n"
                f"User: Calculate 12 * 13\n"
                f"Assistant: I will calculate that.\n"
                f"```python\n"
                f"a = 12\n"
                f"b = 13\n"
                f"print(a * b)\n"
                f"```\n"
                f"Context:\n{context_text}</s>\n"
                f"<|user|>\n"
                f"{query_text}</s>\n"
                f"<|assistant|>\n"
            )

            # 3. Generate
            output = self.safe_generate(prompt, max_tokens=400, stop=["</s>"], echo=False)
            response_text = output['choices'][0]['text'].strip()

            # 4. TOOL USE: Code Execution
            # Regex to find python code blocks
            code_blocks = re.findall(r"```python(.*?)```", response_text, re.DOTALL)
            
            if code_blocks:
                log.info(f"[{self.name}] Code detected. Executing tool...")
                # We execute the last block found (usually the solution)
                code_to_run = code_blocks[-1]
                execution_result = CodeExecutor.execute(code_to_run)
                
                # Append the result to the answer
                response_text += f"\n\n--- 🔧 TOOL OUTPUT ---\n{execution_result}"
                sources.add("Code Interpreter")

            if sources:
                response_text += f"\n\n(Sources: {', '.join(list(sources))})"

            self.publish(EVENT_REASONING_RESPONSE, request_id=request_id, response=response_text)

        except Exception as e:
            log.error(f"[{self.name}] Error: {e}", exc_info=True)
            self.publish(EVENT_REASONING_RESPONSE, request_id=request_id, response="Error thinking.")

    def _on_extract_facts(self, text: str, source: str):
        if not self.llm: return
        log.debug(f"[{self.name}] Extracting logic from: {text[:30]}...")
        
        # Pass the SAFE generator to the engine
        triples = SymbolicEngine.extract_triples(text, self.safe_generate)
        
        if triples:
            count = 0
            for (subj, pred, obj) in triples:
                res = self.memory_manager.add_symbolic_fact(subj, pred, obj, {"source": source})
                if res > 0: count += 1
            if count > 0:
                log.info(f"[{self.name}] Graph Updated: +{count} facts from {source}")

if __name__ == "__main__":
    print("Test via main.py")