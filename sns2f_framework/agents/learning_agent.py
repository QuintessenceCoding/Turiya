# sns2f_framework/agents/learning_agent.py

import logging
import time
from typing import List, Dict

from sns2f_framework.agents.base_agent import BaseAgent
from sns2f_framework.core.event_bus import EventBus, EVENT_LEARNING_NEW_MEMORY
from sns2f_framework.memory.memory_manager import MemoryManager

log = logging.getLogger(__name__)

class LearningAgent(BaseAgent):
    """
    The 'Digestive System' of the swarm.
    
    This agent runs in the background and constantly monitors Short-Term Memory.
    When it finds new observations, it moves them to Long-Term Memory,
    triggering the embedding and indexing process.
    """

    def __init__(self, name: str, event_bus: EventBus, memory_manager: MemoryManager):
        super().__init__(name, event_bus)
        self.memory_manager = memory_manager
        
        # Track stats
        self.memories_consolidated = 0

    def process_step(self):
        """
        Main loop: Check STM, consolidate data if found.
        """
        # 1. Check if there is anything in the inbox (STM)
        # We use the atomic get_and_clear to ensure we own the data.
        observations = self.memory_manager.get_and_clear_observations()
        
        if not observations:
            # Nothing to do, just sleep for a bit (handled by BaseAgent loop)
            return

        # 2. Consolidate the data
        log.debug(f"[{self.name}] Consolidating {len(observations)} items from STM...")
        self._consolidate_batch(observations)

    def _consolidate_batch(self, observations: List[Dict]):
        """
        Process a batch of raw observations and store them in LTM.
        """
        for obs in observations:
            try:
                content = obs['data']
                source = obs.get('source', 'unknown')
                timestamp = obs.get('timestamp')
                
                # Metadata to store with the permanent memory
                metadata = {
                    "original_source": source,
                    "ingested_at": str(timestamp)
                }
                
                # 3. Store in Long-Term Memory (Triggering Vector Compression)
                # The MemoryManager handles the complexity of embedding this text.
                memory_id = self.memory_manager.store_memory(
                    content=content,
                    content_type="observation",
                    metadata=metadata
                )
                
                self.memories_consolidated += 1
                
                # 4. Announce success to the swarm
                # (Other agents might want to know a new memory exists)
                self.publish(EVENT_LEARNING_NEW_MEMORY, memory_id=memory_id)
                
            except Exception as e:
                log.error(f"[{self.name}] Failed to consolidate observation: {e}", exc_info=True)
        
        log.info(f"[{self.name}] Batch complete. Total consolidated: {self.memories_consolidated}")

# --- Self-Test Execution ---
if __name__ == "__main__":
    """
    Test the LearningAgent in isolation.
    Run from root: python -m sns2f_framework.agents.learning_agent
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    import os
    from sns2f_framework.config import DB_PATH

    # Cleanup old DB for a clean test
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    log.info("--- [Test] Testing LearningAgent ---")
    
    # 1. Setup Dependencies
    bus = EventBus()
    mm = MemoryManager()
    
    # 2. Create Agent
    learner = LearningAgent("Learner-01", bus, mm)
    learner.start()
    
    # 3. Simulate Data Arrival (Manually inject into STM)
    log.info("Injecting raw data into Short-Term Memory...")
    mm.add_observation("The sky is blue.", source="test_manual")
    mm.add_observation("Water is wet.", source="test_manual")
    
    # 4. Wait for processing
    # The agent sleeps for 0.1s (AGENT_SLEEP_INTERVAL), so 2 seconds is plenty.
    log.info("Waiting for consolidation...")
    time.sleep(2)
    
    # 5. Verify LTM
    # We search for the memories we just added
    results = mm.find_relevant_memories("What color is the sky?", k=1)
    
    if results:
        best_match = results[0][0]
        score = results[0][1]
        log.info(f"Retrieved from LTM: '{best_match['content']}' (Score: {score:.4f})")
        assert "sky is blue" in best_match['content']
    else:
        log.error("Failed to retrieve memory from LTM!")
        exit(1)

    # 6. Verify STM is empty
    assert len(mm.stm) == 0, "STM should be empty after consolidation"
    
    # 7. Cleanup
    learner.stop()
    learner.join()
    log.info("--- [Test] LearningAgent Test Passed ---")