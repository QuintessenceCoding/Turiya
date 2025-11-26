# sns2f_framework/memory/memory_manager.py

import logging
import threading
import numpy as np
from typing import Any, List, Optional, Tuple, Dict, Union
from datetime import datetime

# Import the individual components that this manager will orchestrate
from .long_term_memory import LongTermMemory
from .short_term_memory import ShortTermMemory
from .neural_compressor import NeuralCompressor
from sns2f_framework.config import EMBEDDING_MODEL_NAME

log = logging.getLogger(__name__)

class MemoryManager:
    """
    The unified facade for the SNS²F memory system.
    
    This class orchestrates all memory components (Short-Term, Long-Term,
    and Neural Compressor) to provide a single, thread-safe API for all
    other agents in the swarm.
    
    It also manages a critical optimization: an in-memory vector cache 
    (self.vector_matrix) for performing lightning-fast, CPU-based 
    similarity searches without hitting the database.
    """

    def __init__(self):
        """
        Initializes all underlying memory components and loads the
        vector cache from persistent storage.
        """
        log.info("Initializing MemoryManager...")
        
        # 1. Instantiate all sub-components
        self.stm = ShortTermMemory()
        self.ltm = LongTermMemory()
        self.compressor = NeuralCompressor()
        
        # 2. Initialize the in-memory vector cache components
        # This cache is a 'shadow' of the LTM's embeddings for fast search.
        
        # Caches all embeddings by their LTM ID
        self._vector_cache: Dict[int, np.ndarray] = {}
        # A single, stacked NumPy matrix of all vectors.
        self._vector_matrix: Optional[np.ndarray] = None
        # A list that maps rows in _vector_matrix back to their LTM ID.
        # e.g., self._vector_id_map[5] gives the memory_id for row 5.
        self._vector_id_map: List[int] = []
        
        # 3. A lock to protect the vector cache during modifications.
        # Any time _vector_cache, _vector_matrix, or _vector_id_map
        # are written, this lock must be held.
        self._cache_lock = threading.Lock()
        
        # 4. Load the vector cache from the LTM database on startup
        self._load_vector_cache()
        log.info("MemoryManager initialized and vector cache loaded.")

    def _load_vector_cache(self):
        """
        Loads all existing embeddings from the LTM (SQLite) into the
        fast, in-memory vector cache (_vector_matrix).
        This is typically called once on startup.
        """
        with self._cache_lock:
            log.debug("Loading vector cache from LTM...")
            # Use the LTM context manager
            with self.ltm as ltm_conn:
                all_memories = ltm_conn.get_all_memories_with_embeddings()
            
            # Clear the existing cache
            self._vector_cache.clear()
            
            if not all_memories:
                log.info("Vector cache is empty. No memories found in LTM.")
                self._vector_matrix = None
                self._vector_id_map.clear()
                return

            # Populate the dictionary cache
            for mem_id, embedding, _ in all_memories:
                self._vector_cache[mem_id] = embedding
            
            # Now, build the searchable matrix
            self._rebuild_vector_matrix_unsafe() # We already hold the lock
            
            log.info(f"Vector cache loaded. {len(self._vector_id_map)} embeddings ready for search.")

    def _rebuild_vector_matrix_unsafe(self):
        """
        Internal method to rebuild the `_vector_matrix` and `_vector_id_map`
        from the `_vector_cache` dict.
        
        WARNING: This method is NOT thread-safe.
        It must be called *only* while holding `self._cache_lock`.
        """
        if not self._vector_cache:
            self._vector_matrix = None
            self._vector_id_map = []
            return

        # Unzip the dictionary into parallel lists
        self._vector_id_map, vectors = zip(*self._vector_cache.items())
        
        # Stack all individual vectors into one large 2D matrix
        # This is the core optimization for fast search.
        self._vector_matrix = np.vstack(vectors).astype(np.float32)
        log.debug(f"Rebuilt vector matrix. Shape: {self._vector_matrix.shape}")

    # --- 1. Short-Term Memory (Working Memory) API ---

    def add_observation(self, data: Any, source: str = "unknown"):
        """
        Adds a new piece of data to the Short-Term Memory (STM).
        This is the "inbox" for the PerceptionAgent.
        
        Args:
            data: The observation (e.g., a chunk of text).
            source: Where the data came from (e.g., URL, user_input).
        """
        observation = {
            "data": data,
            "source": source,
            "timestamp": datetime.now()
        }
        self.stm.add(observation)
        log.debug(f"Added new observation to STM from source: {source}")

    def get_and_clear_observations(self) -> List[Dict]:
        """
        Atomically retrieves all observations from STM and clears it.
        This is the "outbox" for the LearningAgent.
        """
        return self.stm.get_all_and_clear()

    # --- 2. Long-Term Memory (Persistent) API ---

    def store_memory(self, content: str, content_type: str = 'observation', 
                     metadata: Optional[dict] = None) -> int:
        """
        Compresses and permanently stores a new memory (semantic or episodic)
        in the Long-Term Memory (SQLite DB) and updates the in-memory
        vector cache for immediate searchability.
        
        This is a fully transactional, thread-safe operation.

        Args:
            content: The text content to store.
            content_type: A tag (e.g., 'summary', 'raw_text', 'fact').
            metadata: A JSON-serializable dict of context (e.g., source).

        Returns:
            The unique memory_id (int) of the newly stored memory.
        """
        log.debug(f"Storing new memory: '{content[:50]}...'")
        
        # 1. Compress the text into a latent representation (vector)
        embedding = self.compressor.embed(content)
        
        # 2. Store in persistent LTM (SQLite)
        with self.ltm as ltm_conn:
            memory_id = ltm_conn.add_memory_with_embedding(
                content=content,
                embedding=embedding,
                content_type=content_type,
                model_name=self.compressor.model_name,
                metadata=metadata
            )
        
        # 3. Update the fast, in-memory vector cache
        with self._cache_lock:
            self._vector_cache[memory_id] = embedding
            # Rebuild the matrix to include the new vector
            self._rebuild_vector_matrix_unsafe()
            
        log.info(f"Successfully stored and indexed new memory (ID: {memory_id}).")
        return memory_id

    def add_symbolic_fact(self, subject: str, predicate: str, object_val: str, 
                          context: Optional[dict] = None) -> int:
        """
        Stores a symbolic (Subject, Predicate, Object) fact in the LTM.

        Args:
            subject: The subject of the triple (e.g., "SNS2F").
            predicate: The relationship (e.g., "is_a").
            object_val: The object of the triple (e.g., "Framework").
            context: Optional metadata (e.g., source, certainty).
        
        Returns:
            The unique ID of the new fact, or -1 if it already exists.
        """
        with self.ltm as ltm_conn:
            return ltm_conn.add_fact(subject, predicate, object_val, context)

    # --- 3. Retrieval (Reasoning) API ---

    def find_relevant_memories(self, query_text: str, k: int = 5, 
                               min_similarity: float = 0.5) -> List[Tuple[Any, float]]:
        """
        Performs a "neural" search. Finds the top 'k' most relevant memories
        from the LTM based on semantic similarity to a query.

        Args:
            query_text: The text to search for (e.g., "What is sparse activation?").
            k: The maximum number of results to return.
            min_similarity: The minimum similarity score to be included.

        Returns:
            A list of tuples: (memory_row, similarity_score)
            The list is sorted from most to least relevant.
        """
        log.debug(f"Finding relevant memories for query: '{query_text[:50]}...'")
        
        # 1. Compress the query into the same latent space
        query_vector = self.compressor.embed(query_text)
        
        with self._cache_lock:
            # 2. Check if we have anything to search
            if self._vector_matrix is None or self._vector_matrix.shape[0] == 0:
                log.debug("Vector matrix is empty. Cannot perform search.")
                return []
            
            # 3. Perform the search (THE CORE OPERATION)
            # This is a dot product between the (1, 384) query vector and
            # the (N, 384) matrix. Result is a (N,) array of scores.
            # This is extremely fast, even on a CPU.
            similarities = np.dot(self._vector_matrix, query_vector)
            
            # 4. Get the indices of the top k results
            # `argsort` sorts ascending, so we take from the end.
            top_indices = np.argsort(similarities)[-k:][::-1] # [::-1] to reverse
            
            # 5. Map results back to memory IDs and build the result list
            results = []
            with self.ltm as ltm_conn:
                for idx in top_indices:
                    score = float(similarities[idx])
                    
                    if score < min_similarity:
                        continue
                        
                    memory_id = self._vector_id_map[idx]
                    
                    # 6. Retrieve the actual memory content from SQLite
                    memory_data = ltm_conn.get_memory_by_id(memory_id)
                    
                    if memory_data:
                        results.append((dict(memory_data), score))
                        # Update access stats (fire-and-forget for speed)
                        ltm_conn.update_memory_access(memory_id)
                    else:
                        log.warning(f"Vector cache referred to non-existent memory_id: {memory_id}. Cache may be stale.")

        log.debug(f"Found {len(results)} relevant memories.")
        return results

    def find_symbolic_facts(self, subject: Optional[str] = None, 
                            predicate: Optional[str] = None, 
                            object_val: Optional[str] = None) -> List[Any]:
        """
        Performs a "symbolic" search. Finds exact-match triples from the LTM.

        Args:
            subject: The subject to query (e.g., "SNS2F").
            predicate: The predicate to query (e.g., "is_a").
            object_val: The object to query (e.g., "Framework").

        Returns:
            A list of matching row objects.
        """
        log.debug(f"Querying symbolic facts: S={subject}, P={predicate}, O={object_val}")
        with self.ltm as ltm_conn:
            rows = ltm_conn.find_facts(subject, predicate, object_val)
            return [dict(row) for row in rows] # Convert rows to simple dicts

# --- Self-Test Execution ---
if __name__ == "__main__":
    """
    This block allows for direct, local testing of this module.
    You must run this from the project root:
    python -m sns2f_framework.memory.memory_manager
    """
    import os
    from sns2f_framework.config import DB_PATH

    # --- Setup for a clean test ---
    print(f"--- [Test] Pre-Test Cleanup ---")
    if os.path.exists(DB_PATH):
        print(f"Removing old test database: {DB_PATH}")
        os.remove(DB_PATH)
    else:
        print("No old database found. Proceeding.")
    
    # --- Configure basic logging for testing ---
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    log.info("--- [Test] Testing MemoryManager ---")
    
    # 1. Initialization Test
    log.info("Instantiating MemoryManager...")
    manager = MemoryManager()
    assert manager.stm is not None
    assert manager.ltm is not None
    assert manager.compressor is not None
    assert manager._vector_matrix is None # Should be empty on first init
    log.info("MemoryManager instantiated successfully.")

    # 2. STM Test
    log.info("Testing STM functionality...")
    manager.add_observation("Hello world", source="test_run")
    manager.add_observation("Second observation", source="test_run")
    assert len(manager.stm) == 2
    observations = manager.get_and_clear_observations()
    assert len(observations) == 2
    assert len(manager.stm) == 0
    assert observations[0]['data'] == "Hello world"
    log.info("STM add/get/clear test passed.")
    
    # 3. LTM Symbolic Test
    log.info("Testing LTM Symbolic storage...")
    fact_id_1 = manager.add_symbolic_fact("SNS2F", "is_a", "Framework")
    fact_id_2 = manager.add_symbolic_fact("SNS2F", "runs_on", "CPU")
    assert fact_id_1 > 0
    assert fact_id_2 > 0
    
    facts = manager.find_symbolic_facts(subject="SNS2F")
    assert len(facts) == 2
    
    one_fact = manager.find_symbolic_facts(subject="SNS2F", predicate="is_a")
    assert len(one_fact) == 1
    assert one_fact[0]['object_val'] == "Framework"
    log.info("LTM Symbolic storage and retrieval test passed.")
    
    # 4. LTM Neural/Semantic Test
    log.info("Testing LTM Neural/Semantic storage...")
    mem_id_1 = manager.store_memory(
        "Sparse activation means only some modules are active.",
        content_type="fact",
        metadata={"source": "wikipedia"}
    )
    mem_id_2 = manager.store_memory(
        "A hybrid neuro-symbolic system combines logic and patterns.",
        content_type="summary"
    )
    mem_id_3 = manager.store_memory(
        "The quick brown fox jumps over the lazy dog.",
        content_type="noise"
    )
    
    assert manager._vector_matrix is not None
    assert manager._vector_matrix.shape == (3, manager.compressor.dimension)
    assert len(manager._vector_id_map) == 3
    assert mem_id_3 in manager._vector_id_map
    log.info("LTM Neural storage and cache sync test passed.")

    # 5. Neural Retrieval Test
    log.info("Testing Neural retrieval...")
    query = "What is a neuro-symbolic framework?"
    
    results = manager.find_relevant_memories(query, k=1)
    
    assert len(results) == 1
    retrieved_mem = results[0][0]
    retrieved_score = results[0][1]
    
    log.info(f"  -> Query: '{query}'")
    log.info(f"  -> Best match: '{retrieved_mem['content']}' (Score: {retrieved_score:.4f})")
    
    assert retrieved_mem['id'] == mem_id_2
    assert retrieved_score > 0.6 # Should be a reasonably strong match
    
    # 6. Test minimum similarity
    log.info("Testing minimum similarity threshold...")
    # This query is unrelated and should have a low score
    query_unrelated = "What is the capital of France?"
    results_low_score = manager.find_relevant_memories(query_unrelated, k=1, min_similarity=0.9)
    assert len(results_low_score) == 0
    log.info("Minimum similarity threshold test passed.")

    log.info("--- [Test] MemoryManager Test Passed ---")
    
    # --- Cleanup ---
    log.info("--- [Test] Post-Test Cleanup ---")
    if os.path.exists(DB_PATH):
        print(f"Removing test database: {DB_PATH}")
        os.remove(DB_PATH)