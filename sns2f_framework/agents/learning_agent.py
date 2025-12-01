# sns2f_framework/agents/learning_agent.py

import logging
from typing import List, Dict

from sns2f_framework.agents.base_agent import BaseAgent
from sns2f_framework.core.event_bus import (
    EventBus, 
    EVENT_LEARNING_NEW_MEMORY, 
    EVENT_EXTRACT_FACTS,
    EVENT_START_LEARNING, 
    EVENT_STOP_LEARNING   
)
from sns2f_framework.memory.memory_manager import MemoryManager
from sns2f_framework.core.grammar_learner import GrammarLearner

log = logging.getLogger(__name__)

class LearningAgent(BaseAgent):
    """
    The 'Digestive System' of the swarm.
    V7.0: Trust Scoring Enabled.
    """

    def __init__(self, name: str, event_bus: EventBus, memory_manager: MemoryManager):
        super().__init__(name, event_bus)
        self.memory_manager = memory_manager
        self.grammar_learner = GrammarLearner(memory_manager)
        self.memories_consolidated = 0
        self._is_active = True 
        
        self.subscribe(EVENT_START_LEARNING, self._on_start)
        self.subscribe(EVENT_STOP_LEARNING, self._on_stop)

    def _on_start(self):
        log.info(f"[{self.name}] Resuming consolidation.")
        self._is_active = True

    def _on_stop(self):
        log.info(f"[{self.name}] Pausing consolidation.")
        self._is_active = False

    def process_step(self):
        if not self._is_active: return
        observations = self.memory_manager.get_and_clear_observations()
        if not observations: return
        self._consolidate_batch(observations)

    def _consolidate_batch(self, observations: List[Dict]):
        for obs in observations:
            if self._stop_event.is_set(): return
            
            if not self._is_active:
                log.info(f"[{self.name}] Pause detected. Halted batch processing.")
                return 

            try:
                # 1. EXTRACT DATA
                content = obs['data']
                source = obs.get('source', 'unknown')
                timestamp = obs.get('timestamp')
                
                # 2. SOURCE TRUST SCORING
                confidence = 0.5
                if any(d in source for d in ["wikipedia.org", ".edu", ".gov", "nasa.gov"]):
                    confidence = 0.9
                elif "reddit" in source or "twitter" in source:
                    confidence = 0.3
                
                # 3. STORE
                metadata = {
                    "original_source": source,
                    "ingested_at": str(timestamp),
                    "confidence": confidence  # <--- FIX: Use 'confidence' variable
                }
                
                memory_id = self.memory_manager.store_memory(
                    content=content,
                    content_type="observation",
                    metadata=metadata
                )
                
                self.memories_consolidated += 1
                
                # 4. PUBLISH
                self.publish(EVENT_LEARNING_NEW_MEMORY, memory_id=memory_id)
                self.publish(EVENT_EXTRACT_FACTS, text=content, source=source, confidence=confidence)
                
                # Grammar Learning disabled for V6+
                # self.grammar_learner.learn(content)
                
            except Exception as e:
                log.error(f"[{self.name}] Failed to consolidate observation: {e}", exc_info=True)
        
        log.info(f"[{self.name}] Batch complete. Total consolidated: {self.memories_consolidated}")

if __name__ == "__main__":
    print("Please test the LearningAgent via 'python main.py'")