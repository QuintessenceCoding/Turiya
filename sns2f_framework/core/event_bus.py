# sns2f_framework/core/event_bus.py

import threading
from collections import defaultdict
from typing import Callable, Any
import logging

# Configure logger for this module
log = logging.getLogger(__name__)

class EventBus:
    """
    A thread-safe, asynchronous event bus for inter-agent communication.
    
    This enables the "swarm" behavior, where agents can react to events
    from other agents without direct coupling.
    """
    def __init__(self):
        # A dictionary mapping event_type (str) to a list of callbacks (Callable)
        self.listeners: dict[str, list[Callable]] = defaultdict(list)
        # A lock to ensure thread-safety when modifying listeners
        self.lock = threading.Lock()
        log.info("EventBus initialized.")

    def subscribe(self, event_type: str, callback: Callable):
        """
        Subscribe a callback function to a specific event type.
        
        Args:
            event_type: The name of the event to listen for (e.g., "START_LEARNING").
            callback: The function to call when the event is published.
        """
        with self.lock:
            self.listeners[event_type].append(callback)
        log.debug(f"New subscription for event '{event_type}': {callback.__name__}")

    def unsubscribe(self, event_type: str, callback: Callable):
        """
        Remove a callback function from an event type.
        """
        with self.lock:
            if callback in self.listeners[event_type]:
                self.listeners[event_type].remove(callback)
                log.debug(f"Unsubscribed from event '{event_type}': {callback.__name__}")

    def publish(self, event_type: str, *args, **kwargs):
        """
        Publish an event, calling all subscribed callbacks.
        
        This is done synchronously in the publisher's thread.
        For true async, agents should run in their own threads and
        handle events in their own event loops.
        
        Args:
            event_type: The name of the event being published.
            *args: Positional arguments to pass to the callbacks.
            **kwargs: Keyword arguments to pass to the callbacks.
        """
        with self.lock:
            # We copy the list to avoid modification issues during iteration
            callbacks = self.listeners.get(event_type, []).copy()
            
        if callbacks:
            log.debug(f"Publishing event '{event_type}' to {len(callbacks)} listeners.")
        
        for callback in callbacks:
            try:
                # We call the callback directly.
                # The callback (agent) is responsible for its own threading.
                callback(*args, **kwargs)
            except Exception as e:
                log.error(f"Error executing callback {callback.__name__} for event '{event_type}': {e}", exc_info=True)

# --- Define standard system events ---
# These constants will be used throughout the application

# Orchestrator Events
EVENT_SYSTEM_START = "system:start"
EVENT_SYSTEM_SHUTDOWN = "system:shutdown"
EVENT_START_LEARNING = "learning:start"
EVENT_STOP_LEARNING = "learning:stop"
EVENT_SYSTEM_SAVE_CHECKPOINT = "system:checkpoint:save"

# Perception Events
EVENT_PERCEPTION_NEW_DATA = "perception:new_data"

# Learning Events
EVENT_LEARNING_CONSOLIDATE = "learning:consolidate"
EVENT_LEARNING_NEW_FACT = "learning:new_fact"
EVENT_LEARNING_NEW_MEMORY = "learning:new_memory"

# Memory Events
EVENT_MEMORY_STORE_STM = "memory:stm:store"
EVENT_MEMORY_STORE_LTM = "memory:ltm:store"
EVENT_MEMORY_STORE_FACT = "memory:fact:store"
EVENT_MEMORY_RETRIEVE = "memory:retrieve"

# Reasoning Events
EVENT_REASONING_QUERY = "reasoning:query"
EVENT_REASONING_RESPONSE = "reasoning:response"