# sns2f_framework/agents/reasoning_agent.py

import logging
import os
import json
import threading
import re
from collections import deque
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
    V2.3: Hardened Math Mode & History Hygiene.
    """

    def __init__(self, name: str, event_bus: EventBus, memory_manager: MemoryManager):
        super().__init__(name, event_bus)
        self.memory_manager = memory_manager
        self.self_monitor = SelfMonitor(memory_manager)
        self.chat_history = deque(maxlen=6) 

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

    def _critique_answer(self, question: str, answer: str, context: str) -> str:
        # FIX: If the answer contains code, it validates itself. Skip critique.
        if "```python" in answer:
            return answer

        if "No specific information" in context or not context:
            return answer + "\n\n(⚠️ Note: Answer generated without external evidence.)"

        # Standard hallucination check for text answers
        prompt = (
            f"<|system|>\n"
            f"You are a strict Fact Checker. Compare the Answer to the Context.\n"
            f"If the Answer contains facts NOT found in the Context, output 'YES'. Otherwise 'NO'.\n"
            f"Context:\n{context}</s>\n"
            f"Question: {question}\n"
            f"Answer: {answer}</s>\n"
            f"<|user|>\n"
            f"Does the answer contain unsupported facts? Yes/No\n"
            f"<|assistant|>\n"
        )
        try:
            output = self.safe_generate(prompt, max_tokens=5, stop=["\n"], echo=False)
            if "yes" in output['choices'][0]['text'].strip().lower():
                return answer + "\n\n(⚠️ Critic Warning: Answer may contain hallucinations.)"
            return answer
        except:
            return answer

    def _on_query_received(self, query_text: str, request_id: str):
        log.info(f"[{self.name}] Thinking about: '{query_text}'")
        trace_manager.record(request_id, self.name, "Processing Query", query_text)
        
        try:
            # 1. Retrieve
            concepts = self.memory_manager.find_relevant_concepts(query_text, k=2, min_similarity=0.5)
            memories = self.memory_manager.find_relevant_memories(query_text, k=3, min_similarity=0.4)
            trace_manager.record(request_id, self.name, "Retrieval", f"C:{len(concepts)} M:{len(memories)}")

            # 2. Curiosity Check
            peak = max((concepts[0][1] if concepts else 0), (memories[0][1] if memories else 0))
            if peak < 0.5: 
                # Don't trigger search if it's obviously just math
                # Check if query contains math symbols, even if it has words like "what is"
                # We look for at least one operator (+-*/) surrounded by digits
                is_pure_math = bool(re.search(r'\d+\s*[\+\-\*\/]\s*\d+', query_text))
                if not is_pure_math:
                    topic = self._extract_topic(query_text)
                    self.publish(EVENT_GAP_DETECTED, topic=topic, request_id=request_id)

            # 3. Context Building
            context_text = ""
            sources = set()
            
            # Self-Reflect
            if any(t in query_text.lower() for t in ["you", "your", "self", "turiya"]):
                context_text += f"{self.self_monitor.get_system_report()}\n\n"
                sources.add("Self-Monitor")

            if concepts:
                for c, _ in concepts: context_text += f"Concept: {c['name']}: {c['definition']}\n"
            if memories:
                for m, _ in memories: 
                    context_text += f"Fact: {m['content']}\n"
                    sources.add(json.loads(m['metadata']).get('original_source', 'unknown'))

            if not context_text: context_text = "No specific information found."

            # 4. PROMPT SELECTION (The Math Fix)
            # Detect math symbols or keywords
            is_math = bool(re.search(r'\d+\s*[\+\-\*\/]\s*\d+', query_text)) or \
                      any(w in query_text.lower() for w in ["calculate", "compute", "solve", "math"])

            if is_math:
                # SPECIAL CALCULATOR PROMPT
                trace_manager.record(request_id, self.name, "Mode Switch", "Calculator Persona Activated")
                prompt = (
                    f"<|system|>\n"
                    f"You are a Python Calculator. User wants math. Write a script to solve it.\n"
                    f"RULES: Define variables. Print the result.\n"
                    f"Example:\nUser: 10 * 10\n```python\na=10\nb=10\nprint(a*b)\n```\n"
                    f"<|user|>\n"
                    f"{query_text}</s>\n"
                    f"<|assistant|>\n"
                )
            else:
                # STANDARD RAG PROMPT
                history_text = ""
                for msg in self.chat_history:
                    role = "<|user|>" if msg['role'] == 'user' else "<|assistant|>"
                    history_text += f"{role}\n{msg['content']}</s>\n"

                prompt = (
                    f"<|system|>\n"
                    f"You are Turiya. Answer using Context. If code is needed, use ```python```.\n"
                    f"Context:\n{context_text}</s>\n"
                    f"{history_text}"
                    f"<|user|>\n"
                    f"{query_text}</s>\n"
                    f"<|assistant|>\n"
                )

            # 5. Generation
            output = self.safe_generate(prompt, max_tokens=400, stop=["</s>"], echo=False)
            raw_response = output['choices'][0]['text'].strip()

            # 6. Critic (Skipped if math detected to avoid noise)
            if is_math:
                response_text = raw_response
            else:
                response_text = self._critique_answer(query_text, raw_response, context_text)

            # 7. Tool Execution
            code_blocks = re.findall(r"```python(.*?)```", response_text, re.DOTALL)
            if code_blocks:
                trace_manager.record(request_id, self.name, "Tool Usage", "Executing Code")
                execution_result = CodeExecutor.execute(code_blocks[-1])
                response_text += f"\n\n--- 🔧 TOOL OUTPUT ---\n{execution_result}"
                sources.add("Code Interpreter")

            if sources and not is_math:
                response_text += f"\n\n(Sources: {', '.join(list(sources))})"

            # 8. History Hygiene (Prevent warning loops)
            self.chat_history.append({'role': 'user', 'content': query_text})
            # Remove sources AND warnings before saving to history
            clean_response = response_text.split('\n\n(Sources:')[0]
            clean_response = clean_response.split('\n\n(⚠️')[0] 
            clean_response = clean_response.split('\n\n--- 🔧')[0] # Don't save tool output to history (saves context window space)
            self.chat_history.append({'role': 'assistant', 'content': clean_response})

            self.publish(EVENT_REASONING_RESPONSE, request_id=request_id, response=response_text)
            
        except Exception as e:
            log.error(f"[{self.name}] Error: {e}", exc_info=True)
            self.publish(EVENT_REASONING_RESPONSE, request_id=request_id, response="Error thinking.")

    # (Keep _on_extract_facts and _extract_topic as they were)
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
        # Simple extraction logic
        prompt = f"Extract keyword:\nQuestion: Who is Turing?\nKeyword: Turing\nQuestion: {query}\nKeyword:"
        try:
            output = self.safe_generate(prompt, max_tokens=10, stop=["\n"], echo=False)
            return output['choices'][0]['text'].strip() or query
        except:
            return query

if __name__ == "__main__":
    print("Test via main.py")