# sns2f_framework/agents/base_agent.py

import threading
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional

from sns2f_framework.config import AGENT_SLEEP_INTERVAL
from sns2f_framework.core.event_bus import EventBus

log = logging.getLogger(__name__)

class BaseAgent(ABC, threading.Thread):
    """
    The abstract base class for all agents in the SNS²F swarm.
    
    It handles:
    1. Threading (each agent runs in its own thread).
    2. Event Bus connection (publishing/subscribing).
    3. Lifecycle management (start, stop, loop).
    
    Subclasses must implement the `process_step()` method.
    """
    
    def __init__(self, name: str, event_bus: EventBus):
        super().__init__()
        self.name = name
        self.event_bus = event_bus
        
        # Threading control flags
        self._stop_event = threading.Event()
        self._is_running = False
        
        
        
        # Daemon threads die automatically when the main program exits
        self.daemon = True 

    def run(self):
        """
        The main entry point for the thread.
        Do not override this. Override `process_step` instead.
        """
        log.info(f"Agent '{self.name}' starting...")
        self._is_running = True
        
        try:
            self.setup()
            
            while not self._stop_event.is_set():
                # perform one unit of work
                self.process_step()
                
                # Sleep briefly to prevent CPU hogging
                time.sleep(AGENT_SLEEP_INTERVAL)
                
        except Exception as e:
            log.error(f"Agent '{self.name}' crashed: {e}", exc_info=True)
        finally:
            self.teardown()
            self._is_running = False
            log.info(f"Agent '{self.name}' stopped.")

    def stop(self):
        """
        Signals the agent to stop nicely.
        """
        log.info(f"Agent '{self.name}' received stop signal.")
        self._stop_event.set()

    def setup(self):
        """
        Optional: Override this to perform one-time setup before the loop starts.
        """
        pass

    def teardown(self):
        """
        Optional: Override this to perform cleanup after the loop ends.
        """
        pass

    @abstractmethod
    def process_step(self):
        """
        The core logic of the agent. This is called repeatedly in the loop.
        MUST be implemented by subclasses.
        """
        pass

    # --- Helper wrappers for the Event Bus ---

    def publish(self, event_type: str, *args, **kwargs):
        """Helper to publish an event to the swarm."""
        self.event_bus.publish(event_type, *args, **kwargs)

    def subscribe(self, event_type: str, callback):
        """Helper to subscribe to a swarm event."""
        self.event_bus.subscribe(event_type, callback)

# --- Self-Test Execution ---
if __name__ == "__main__":
    """
    Test the BaseAgent by creating a dummy implementation.
    Run: python -m sns2f_framework.agents.base_agent
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    # Define a simple Test Agent
    class TestAgent(BaseAgent):
        def setup(self):
            self.counter = 0
            log.info(f"{self.name} is setting up.")

        def process_step(self):
            self.counter += 1
            log.info(f"{self.name} step {self.counter}")
            if self.counter >= 3:
                self.stop() # Self-terminate after 3 steps

        def teardown(self):
            log.info(f"{self.name} says goodbye.")

    # Run the test
    log.info("--- [Test] Testing BaseAgent ---")
    
    # 1. Create Event Bus (dependency)
    bus = EventBus()
    
    # 2. Create Agent
    agent = TestAgent(name="Tester-01", event_bus=bus)
    
    # 3. Start Agent
    agent.start()
    
    # 4. Wait for it to finish (join)
    agent.join(timeout=2)
    
    if agent.is_alive():
        log.error("Agent failed to stop in time!")
    else:
        log.info("Agent stopped successfully.")
    
    log.info("--- [Test] BaseAgent Test Passed ---")