# sns2f_framework/memory/short_term_memory.py

import logging
import threading
from collections import deque
from typing import Any, List, Optional

# We attempt to load the project config dynamically to avoid static-import resolution
# errors in editors/linters while still using the real config at runtime.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Help static type checkers know the symbol exists without forcing a runtime import.
    try:
        from sns2f_framework.config import STM_CAPACITY  # type: ignore
    except Exception:
        STM_CAPACITY = 100  # fallback for type-checker contexts

# Runtime: import dynamically so editors that can't resolve the package won't error.
try:
    import importlib

    cfg = importlib.import_module("sns2f_framework.config")
    STM_CAPACITY = getattr(cfg, "STM_CAPACITY", 100)
except Exception:
    # Fallback default when the project config module is unavailable (e.g., during static analysis or isolated editing)
    STM_CAPACITY = 100  # sensible default value
    logging.getLogger(__name__).warning(
        "Could not import sns2f_framework.config.STM_CAPACITY; using default %d", STM_CAPACITY
    )

# Set up logging for this module
log = logging.getLogger(__name__)

class ShortTermMemory:
    """
    A thread-safe, in-memory, fixed-capacity "working memory" buffer.
    
    This class is implemented as a deque (double-ended queue). When the
    memory is full and a new item is added, the oldest item is
    automatically discarded.
    
    This is used as the initial "inbox" for the PerceptionAgent. New data
    lands here before the LearningAgent can process and consolidate it
    into LongTermMemory.
    """
    
    def __init__(self, capacity: int = STM_CAPACITY):
        """
        Initializes the short-term memory store.

        Args:
            capacity: The maximum number of items the STM can hold.
        """
        if capacity <= 0:
            raise ValueError("STM capacity must be a positive integer")
            
        self.capacity = capacity
        # A deque with a 'maxlen' automatically handles its own size,
        # evicting old items from the opposite end when full.
        self._memory: deque = deque(maxlen=self.capacity)
        
        # A lock is crucial to prevent race conditions.
        self._lock = threading.Lock()
        
        log.info(f"ShortTermMemory initialized with capacity {self.capacity}")

    def add(self, item: Any):
        """
        Adds a new item to the short-term memory.
        
        If the memory is full, the oldest item is automatically
        discarded (popped from the left). This is a thread-safe operation.

        Args:
            item: The data item to store (e.g., a text observation, a tuple).
        """
        with self._lock:
            self._memory.append(item)
        log.debug(f"Added item to STM. Current size: {len(self._memory)}")

    def get_all_and_clear(self) -> List[Any]:
        """
        Atomically retrieves all items from the STM and clears it.
        
        This is the primary method used by the LearningAgent to "consume"
        the contents of working memory for consolidation.
        
        This is a thread-safe operation.

        Returns:
            A list of all items that were in the STM, in order of arrival.
        """
        with self._lock:
            # We convert the deque to a list
            items = list(self._memory)
            # We clear the underlying deque
            self._memory.clear()
            
        if items:
            log.debug(f"Retrieved and cleared {len(items)} items from STM.")
        return items

    def peek(self) -> Optional[Any]:
        """
        Returns the most recently added item without removing it.
        
        Returns None if the memory is empty.
        This is a thread-safe operation.
        """
        with self._lock:
            if not self._memory:
                return None
            # -1 index gets the rightmost (most recent) item
            return self._memory[-1]

    def clear(self):
        """
        Clears all items from the short-term memory.
        This is a thread-safe operation.
        """
        with self._lock:
            self._memory.clear()
        log.info("ShortTermMemory cleared.")

    def __len__(self) -> int:
        """
        Returns the current number of items in the STM.
        This is a thread-safe operation.
        """
        with self._lock:
            return len(self._memory)

# --- Self-Test Execution ---
if __name__ == "__main__":
    """
    This block allows for direct, local testing of this module.
    You can run this file directly: python -m sns2f_framework.memory.short_term_memory
    """
    
    import time

    # --- Configure basic logging for testing ---
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    log.info("--- [Test] Testing ShortTermMemory ---")
    
    # Define a local capacity just for this test
    TEST_CAPACITY = 5 
    
    # 1. Test Initialization and Capacity
    log.info(f"Using local test capacity: {TEST_CAPACITY}")
    # We pass our local test capacity to the constructor here
    stm = ShortTermMemory(capacity=TEST_CAPACITY)
    assert stm.capacity == TEST_CAPACITY, f"Capacity should be {TEST_CAPACITY}"
    
    # 2. Test Adding Items
    log.info("Adding 3 items...")
    stm.add("Observation 1")
    stm.add("Observation 2")
    stm.add("Observation 3")
    log.info(f"Current STM size: {len(stm)}")
    assert len(stm) == 3, "Size should be 3"
    
    # 3. Test 'peek'
    log.info("Peeking at last item...")
    last_item = stm.peek()
    log.info(f"  -> Peeked item: '{last_item}'")
    assert last_item == "Observation 3", "Peeked item is incorrect"
    assert len(stm) == 3, "Size should still be 3 after peek"
    
    # 4. Test Capacity Limit
    log.info("Adding 3 more items to test eviction...")
    stm.add("Observation 4")
    stm.add("Observation 5")
    stm.add("Observation 6") # This should evict "Observation 1"
    
    log.info(f"Current STM size: {len(stm)}")
    assert len(stm) == TEST_CAPACITY, f"Size should be capped at {TEST_CAPACITY}"
    
    # 5. Test 'get_all_and_clear'
    log.info("Getting all and clearing...")
    all_items = stm.get_all_and_clear()
    
    log.info(f"  -> Retrieved items: {all_items}")
    log.info(f"  -> Size after clear: {len(stm)}")
    
    expected_items = [
        "Observation 2", 
        "Observation 3", 
        "Observation 4", 
        "Observation 5", 
        "Observation 6"
    ]
    assert all_items == expected_items, "Eviction order is incorrect"
    assert len(stm) == 0, "Size should be 0 after clear"

    # 6. Test 'clear'
    log.info("Adding 2 items and then calling clear()...")
    stm.add("Item A")
    stm.add("Item B")
    log.info(f"  -> Size before clear: {len(stm)}")
    stm.clear()
    log.info(f"  -> Size after clear: {len(stm)}")
    assert len(stm) == 0, "Clear method failed"

    log.info("--- [Test] ShortTermMemory Test Passed ---")