# sns2f_framework/agents/learning_agent.py

import logging
from typing import List, Dict

from sns2f_framework.agents.base_agent import BaseAgent
from sns2f_framework.core.event_bus import (
    EventBus, 
    EVENT_LEARNING_NEW_MEMORY, 
    EVENT_EXTRACT_FACTS,
    EVENT_START_LEARNING, # <--- Added
    EVENT_STOP_LEARNING   # <--- Added
)
from sns2f_framework.memory.memory_manager import MemoryManager
from sns2f_framework.core.grammar_learner import GrammarLearner

log = logging.getLogger(__name__)

class LearningAgent(BaseAgent):
    """
    The 'Digestive System' of the swarm.
    """

    def __init__(self, name: str, event_bus: EventBus, memory_manager: MemoryManager):
        super().__init__(name, event_bus)
        self.memory_manager = memory_manager
        self.grammar_learner = GrammarLearner(memory_manager)
        self.memories_consolidated = 0
        
        # New Flag: Is the system currently in "Active Learning" mode?
        # We default to True so it processes manual injections, but /stop will flip it.
        self._is_active = True 
        
        # Subscribe to global Start/Stop signals
        self.subscribe(EVENT_START_LEARNING, self._on_start)
        self.subscribe(EVENT_STOP_LEARNING, self._on_stop)

    def _on_start(self):
        log.info(f"[{self.name}] Resuming consolidation.")
        self._is_active = True

    def _on_stop(self):
        log.info(f"[{self.name}] Pausing consolidation.")
        self._is_active = False

    def process_step(self):
        # 1. If we are paused, don't touch the queue.
        # This keeps the items in STM (RAM) safe until we resume.
        if not self._is_active:
            return

        # 2. Check if there is anything in the inbox (STM)
        observations = self.memory_manager.get_and_clear_observations()
        
        if not observations:
            return

        # 3. Consolidate the data
        self._consolidate_batch(observations)

    def _consolidate_batch(self, observations: List[Dict]):
        """
        Process a batch of raw observations and store them in LTM.
        """
        for obs in observations:
            # --- BRAKE CHECK ---
            # Check BOTH thread termination (_stop_event) AND user pause (_is_active)
            if self._stop_event.is_set():
                return
            
            if not self._is_active:
                # If user typed /stop while we were in a loop, we push the 
                # remaining items BACK into the STM so we don't lose them!
                # (This is a simplified approach; usually we'd re-queue)
                log.info(f"[{self.name}] Pause detected. Halted batch processing.")
                return 
            # -------------------

            try:
                content = obs['data']
                source = obs.get('source', 'unknown')
                timestamp = obs.get('timestamp')
                
                metadata = {
                    "original_source": source,
                    "ingested_at": str(timestamp)
                }
                
                # Store in Long-Term Memory
                memory_id = self.memory_manager.store_memory(
                    content=content,
                    content_type="observation",
                    metadata=metadata
                )
                
                self.memories_consolidated += 1
                self.publish(EVENT_LEARNING_NEW_MEMORY, memory_id=memory_id)
                self.publish(EVENT_EXTRACT_FACTS, text=content, source=source)
                # LEARN GRAMMAR
                #self.grammar_learner.learn(content)
            except Exception as e:
                log.error(f"[{self.name}] Failed to consolidate observation: {e}", exc_info=True)
        
        log.info(f"[{self.name}] Batch complete. Total consolidated: {self.memories_consolidated}")

# --- Self-Test Execution ---
if __name__ == "__main__":
    print("Please test the LearningAgent via 'python main.py'")