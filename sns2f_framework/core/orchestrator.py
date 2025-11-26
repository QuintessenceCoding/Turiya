# sns2f_framework/core/orchestrator.py

import logging
import time
import uuid
from typing import Callable, Optional

from sns2f_framework.core.event_bus import (
    EventBus, 
    EVENT_START_LEARNING, 
    EVENT_STOP_LEARNING, 
    EVENT_REASONING_QUERY, 
    EVENT_REASONING_RESPONSE,
    EVENT_SYSTEM_SHUTDOWN
)
from sns2f_framework.memory.memory_manager import MemoryManager
from sns2f_framework.agents.perception_agent import PerceptionAgent
from sns2f_framework.agents.learning_agent import LearningAgent
from sns2f_framework.agents.reasoning_agent import ReasoningAgent

log = logging.getLogger(__name__)

class Orchestrator:
    """
    The main controller for the SNS²F system.
    
    It initializes the infrastructure (EventBus, Memory) and the Swarm (Agents).
    It exposes high-level methods to control the system from the CLI.
    """

    def __init__(self):
        log.info("Booting SNS²F Orchestrator...")
        
        # 1. Initialize Infrastructure
        self.bus = EventBus()
        self.memory_manager = MemoryManager()
        
        # 2. Initialize Agents
        # We pass the bus and memory manager to them so they are connected.
        self.perception_agent = PerceptionAgent("Perception", self.bus, self.memory_manager)
        self.learning_agent = LearningAgent("Learning", self.bus, self.memory_manager)
        self.reasoning_agent = ReasoningAgent("Reasoning", self.bus, self.memory_manager)
        
        self.agents = [
            self.perception_agent,
            self.learning_agent,
            self.reasoning_agent
        ]
        
        # Callback for handling answers coming back from the reasoning agent
        self._response_callback: Optional[Callable] = None
        self.bus.subscribe(EVENT_REASONING_RESPONSE, self._handle_reasoning_response)

    def start(self):
        """Starts all agents in the swarm."""
        log.info("Starting swarm agents...")
        for agent in self.agents:
            agent.start()
        log.info("System is live and ready.")

    def stop(self):
        """Stops all agents and shuts down the system."""
        log.info("Shutting down system...")
        self.bus.publish(EVENT_SYSTEM_SHUTDOWN)
        
        for agent in self.agents:
            agent.stop()
            
        # Wait for threads to finish
        for agent in self.agents:
            agent.join()
        
        log.info("System shutdown complete.")

    # --- High-Level Commands ---

    def start_learning(self):
        """Signals the swarm to begin active learning (Perception)."""
        log.info("Command: START LEARNING")
        self.bus.publish(EVENT_START_LEARNING)

    def stop_learning(self):
        """Signals the swarm to stop active learning."""
        log.info("Command: STOP LEARNING")
        self.bus.publish(EVENT_STOP_LEARNING)

    def ask(self, question: str, callback: Callable):
        """
        Submits a query to the reasoning agent.
        
        Args:
            question: The text query.
            callback: A function to call when the answer is ready.
        """
        request_id = str(uuid.uuid4())
        self._response_callback = callback
        
        log.info(f"Command: ASK '{question}' (ID: {request_id})")
        self.bus.publish(EVENT_REASONING_QUERY, query_text=question, request_id=request_id)

    def _handle_reasoning_response(self, request_id: str, response: str):
        """Internal handler to route the answer back to the CLI."""
        if self._response_callback:
            self._response_callback(response)