# sns2f_framework/core/orchestrator.py

import logging
import uuid
from typing import Callable, Optional

from sns2f_framework.core.event_bus import (
    EventBus, EVENT_START_LEARNING, EVENT_STOP_LEARNING, 
    EVENT_REASONING_QUERY, EVENT_REASONING_RESPONSE, EVENT_SYSTEM_SHUTDOWN
)
from sns2f_framework.memory.memory_manager import MemoryManager
from sns2f_framework.agents.perception_agent import PerceptionAgent
from sns2f_framework.agents.learning_agent import LearningAgent
from sns2f_framework.agents.reasoning_agent import ReasoningAgent
from sns2f_framework.reasoning.concept_miner import ConceptMiner
from sns2f_framework.reasoning.consolidator import Consolidator
from sns2f_framework.core.trace_manager import trace_manager

log = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        log.info("Booting SNS²F Orchestrator...")
        self.bus = EventBus()
        self.memory_manager = MemoryManager()
        
        self.perception_agent = PerceptionAgent("Perception", self.bus, self.memory_manager)
        self.learning_agent = LearningAgent("Learning", self.bus, self.memory_manager)
        self.reasoning_agent = ReasoningAgent("Reasoning", self.bus, self.memory_manager)
        
        self.agents = [self.perception_agent, self.learning_agent, self.reasoning_agent]
        self._response_callback: Optional[Callable] = None
        self.bus.subscribe(EVENT_REASONING_RESPONSE, self._handle_reasoning_response)

    def start(self):
        for agent in self.agents: agent.start()
        log.info("System is live.")

    def stop(self):
        self.bus.publish(EVENT_SYSTEM_SHUTDOWN)
        for agent in self.agents: agent.stop()
        for agent in self.agents: agent.join()

    def start_learning(self):
        self.bus.publish(EVENT_START_LEARNING)

    def stop_learning(self):
        self.bus.publish(EVENT_STOP_LEARNING)

    def consolidate_knowledge(self):
        """
        Triggers the Concept Evolution Cycle.
        V4 Update: Enabled for Symbolic Mode (No LLM needed).
        """
        log.info("Command: CONSOLIDATE KNOWLEDGE")
        # Initialize Miner without LLM (it uses symbolic synthesis now)
        miner = ConceptMiner(self.memory_manager)
        count = miner.run_mining_cycle()
        
        # Reload caches so the Reasoning Agent sees the new concepts immediately
        self.memory_manager._load_caches()
        
        return count

    def sleep_cycle(self):
        log.info("Command: SLEEP CYCLE")
        self.stop_learning()
        janitor = Consolidator(self.memory_manager)
        stats = janitor.run_sleep_cycle()
        return stats

    def ask(self, question: str, callback: Callable, request_id: str = None):
        if not request_id:
            request_id = str(uuid.uuid4())
            
        self._response_callback = callback
        trace_manager.record(request_id, "Orchestrator", "Query Submitted", question)
        log.info(f"Command: ASK '{question}' (ID: {request_id})")
        self.bus.publish(EVENT_REASONING_QUERY, query_text=question, request_id=request_id)

    def _handle_reasoning_response(self, request_id: str, response: str):
        if self._response_callback:
            self._response_callback(response)