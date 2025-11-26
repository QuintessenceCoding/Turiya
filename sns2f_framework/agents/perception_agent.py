# sns2f_framework/agents/perception_agent.py

import logging
import time
import random
from typing import Optional

from sns2f_framework.agents.base_agent import BaseAgent
from sns2f_framework.core.event_bus import EventBus, EVENT_START_LEARNING, EVENT_STOP_LEARNING, EVENT_PERCEPTION_NEW_DATA
from sns2f_framework.memory.memory_manager import MemoryManager
from sns2f_framework.config import WHITELISTED_SOURCES

log = logging.getLogger(__name__)

class PerceptionAgent(BaseAgent):
    """
    The 'Eyes' of the swarm.
    
    This agent monitors external data sources. When the system enters
    'Learning Mode', it autonomously fetches content from whitelisted
    sources and pushes it into the Short-Term Memory (STM).
    """

    def __init__(self, name: str, event_bus: EventBus, memory_manager: MemoryManager):
        super().__init__(name, event_bus)
        self.memory_manager = memory_manager
        
        # State: Is the agent currently actively looking for info?
        self._is_learning = False
        
        # Subscribe to global commands
        self.subscribe(EVENT_START_LEARNING, self._on_start_learning)
        self.subscribe(EVENT_STOP_LEARNING, self._on_stop_learning)

    def _on_start_learning(self):
        """Event handler: Wake up and start reading."""
        log.info(f"[{self.name}] Received START_LEARNING command. Engaging sensors.")
        self._is_learning = True

    def _on_stop_learning(self):
        """Event handler: Stop reading."""
        log.info(f"[{self.name}] Received STOP_LEARNING command. Idling.")
        self._is_learning = False

    def process_step(self):
        """
        The main loop. If learning is active, fetch data and store it.
        """
        if not self._is_learning:
            # If we aren't learning, just sleep and do nothing
            return

        # 1. Pick a source to 'read' from
        source_url = self._pick_random_source()
        
        # 2. Fetch the content (Simulated for this build)
        content = self._fetch_content(source_url)
        
        if content:
            # 3. Store raw data in Short-Term Memory
            self.memory_manager.add_observation(content, source=source_url)
            
            # 4. Notify the swarm that new data is available
            self.publish(EVENT_PERCEPTION_NEW_DATA, source=source_url)
            
            log.debug(f"[{self.name}] Ingested data from {source_url}")
            
            # 5. Artificial delay to simulate reading time and prevent spamming
            time.sleep(1.5) 

    def _pick_random_source(self) -> str:
        """Selects a random source from the whitelist."""
        if not WHITELISTED_SOURCES:
            return "internal_simulation"
        return random.choice(WHITELISTED_SOURCES)

    def _fetch_content(self, url: str) -> str:
        """
        Simulates reading content from a URL.
        
        In a production V2, this would use `requests.get(url)`.
        For now, we generate relevant synthetic text to test the pipeline.
        """
        # A small dictionary of "knowledge" to simulate reading different sites
        simulated_knowledge = [
            "Neuro-symbolic AI combines neural networks' pattern recognition with symbolic logic's reasoning.",
            "Sparse activation reduces computational cost by only using relevant neurons for a task.",
            "The event bus allows asynchronous communication between decoupled agents.",
            "Long-term memory consolidation involves compressing episodic memories into semantic facts.",
            "Swarm intelligence emerges from the interaction of many simple agents.",
            "Latent representations allow complex data to be stored as compact vectors.",
            "Plasticity in AI refers to the ability to rewire connections based on new data."
        ]
        
        # Return a random "fact" simulating a sentence read from a webpage
        return random.choice(simulated_knowledge)

# --- Self-Test Execution ---
if __name__ == "__main__":
    """
    Test the PerceptionAgent in isolation.
    Run from root: python -m sns2f_framework.agents.perception_agent
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    log.info("--- [Test] Testing PerceptionAgent ---")
    
    # 1. Setup Dependencies
    bus = EventBus()
    mm = MemoryManager()
    
    # 2. Create Agent
    agent = PerceptionAgent("Perception-01", bus, mm)
    agent.start()
    
    # 3. Test: Agent should be idle initially
    log.info("Agent started. Waiting 1 second (should be idle)...")
    time.sleep(1)
    # Check STM (should be empty)
    assert len(mm.stm) == 0, "STM should be empty before learning starts"
    
    # 4. Test: Start Learning
    log.info(">>> sending START_LEARNING event")
    bus.publish(EVENT_START_LEARNING)
    
    # Let it run for 4 seconds (should read ~2 items)
    time.sleep(4)
    
    # 5. Test: Stop Learning
    log.info(">>> sending STOP_LEARNING event")
    bus.publish(EVENT_STOP_LEARNING)
    
    # 6. Verify Results
    items = mm.get_and_clear_observations()
    log.info(f"Items captured in STM: {len(items)}")
    
    assert len(items) > 0, "Agent failed to capture data during learning mode"
    log.info(f"Sample data: {items[0]}")
    
    # 7. Cleanup
    agent.stop()
    agent.join()
    log.info("--- [Test] PerceptionAgent Test Passed ---")