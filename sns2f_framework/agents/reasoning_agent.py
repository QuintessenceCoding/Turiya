# sns2f_framework/agents/reasoning_agent.py

import logging
import time
import json
from typing import Dict, Any

from sns2f_framework.agents.base_agent import BaseAgent
from sns2f_framework.core.event_bus import (
    EventBus, 
    EVENT_REASONING_QUERY, 
    EVENT_REASONING_RESPONSE
)
from sns2f_framework.memory.memory_manager import MemoryManager

log = logging.getLogger(__name__)

class ReasoningAgent(BaseAgent):
    """
    The 'Brain' of the swarm.
    
    This agent listens for queries, performs hybrid neuro-symbolic searches
    against the Long-Term Memory, and returns the most relevant information.
    """

    def __init__(self, name: str, event_bus: EventBus, memory_manager: MemoryManager):
        super().__init__(name, event_bus)
        self.memory_manager = memory_manager
        
        # Subscribe to incoming questions
        self.subscribe(EVENT_REASONING_QUERY, self._on_query_received)

    def process_step(self):
        """
        The ReasoningAgent is purely event-driven. 
        It sleeps until a query arrives via the EventBus.
        """
        pass

    def _on_query_received(self, query_text: str, request_id: str):
        """
        Triggered when a user (or another agent) asks a question.
        """
        log.info(f"[{self.name}] Processing query: '{query_text}' (ID: {request_id})")
        
        try:
            # 1. Neural Search (The "Intuition")
            # Find memories that are semantically similar to the query.
            neural_results = self.memory_manager.find_relevant_memories(
                query_text, k=3, min_similarity=0.4
            )
            
            # 2. Symbolic Search (The "Logic") - Placeholder for V1
            # In a full V2, we would parse the query for entities (e.g., "SNS2F")
            # and look up specific facts in the graph.
            # facts = self.memory_manager.find_symbolic_facts(subject="SNS2F")
            
            # 3. Synthesize Answer
            # For this V1 non-LLM build, we select the best context found.
            if neural_results:
                best_memory = neural_results[0][0]
                score = neural_results[0][1]
                
                response_text = (
                    f"Based on my memory (Confidence: {score:.2f}):\n"
                    f"{best_memory['content']}\n"
                    f"(Source: {json.loads(best_memory['metadata']).get('original_source', 'unknown')})"
                )
            else:
                response_text = "I have no memory of anything related to that."

            # 4. Publish the Answer
            self.publish(
                EVENT_REASONING_RESPONSE, 
                request_id=request_id, 
                response=response_text
            )
            log.info(f"[{self.name}] Answer published for ID: {request_id}")

        except Exception as e:
            log.error(f"[{self.name}] Error processing query: {e}", exc_info=True)
            self.publish(
                EVENT_REASONING_RESPONSE, 
                request_id=request_id, 
                response="Error processing query."
            )

# --- Self-Test Execution ---
if __name__ == "__main__":
    """
    Test the ReasoningAgent in isolation.
    Run from root: python -m sns2f_framework.agents.reasoning_agent
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    import os
    import uuid
    from sns2f_framework.config import DB_PATH

    # Cleanup old DB for a clean test
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except:
            pass

    log.info("--- [Test] Testing ReasoningAgent ---")
    
    # 1. Setup Dependencies
    bus = EventBus()
    mm = MemoryManager()
    
    # 2. Seed Memory (We need something to find!)
    log.info("Seeding LTM with knowledge...")
    mm.store_memory(
        "The SNS2F framework uses sparse activation to save energy.",
        metadata={"original_source": "manual_seed"}
    )
    # Wait for the cache update
    time.sleep(0.5) 
    
    # 3. Create & Start Agent
    agent = ReasoningAgent("Brain-01", bus, mm)
    agent.start()
    
    # 4. Define a Listener to capture the response
    response_received = {}
    
    def capture_response(request_id, response):
        log.info(f">>> CAPTURED RESPONSE: {response}")
        response_received['id'] = request_id
        response_received['text'] = response
        
    bus.subscribe(EVENT_REASONING_RESPONSE, capture_response)
    
    # 5. Send Query
    req_id = str(uuid.uuid4())
    query = "How does SNS2F save energy?"
    log.info(f"Sending query: '{query}'")
    
    bus.publish(EVENT_REASONING_QUERY, query_text=query, request_id=req_id)
    
    # 6. Wait for response
    time.sleep(2)
    
    # 7. Verify
    if response_received.get('id') == req_id:
        log.info("Success! Response matched request ID.")
        assert "sparse activation" in response_received['text']
    else:
        log.error("Test Failed: No response received.")
        exit(1)
        
    agent.stop()
    agent.join()
    log.info("--- [Test] ReasoningAgent Test Passed ---")