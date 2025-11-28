# sns2f_framework/memory/memory_manager.py

import logging
import threading
import numpy as np
from typing import Any, List, Optional, Tuple, Dict
from datetime import datetime

from .long_term_memory import LongTermMemory
from .short_term_memory import ShortTermMemory
from .neural_compressor import NeuralCompressor

log = logging.getLogger(__name__)

class MemoryManager:
    """
    The unified facade for the SNS²F memory system.
    V2: Now manages TWO vector spaces (Memories and Concepts).
    """

    def __init__(self):
        log.info("Initializing MemoryManager...")
        self.stm = ShortTermMemory()
        self.ltm = LongTermMemory()
        self.compressor = NeuralCompressor()
        
        # --- CACHE 1: RAW MEMORIES ---
        self._vector_cache: Dict[int, np.ndarray] = {}
        self._vector_matrix: Optional[np.ndarray] = None
        self._vector_id_map: List[int] = []
        
        # --- CACHE 2: CONCEPTS ---
        self._concept_cache: Dict[int, np.ndarray] = {}
        self._concept_matrix: Optional[np.ndarray] = None
        self._concept_id_map: List[int] = []

        self._cache_lock = threading.Lock()
        
        # Load both caches
        self._load_caches()

    def _load_caches(self):
        """Loads both memory and concept vectors from SQLite to RAM."""
        with self._cache_lock:
            # 1. Load Memories
            with self.ltm as conn:
                mems = conn.get_all_memories_with_embeddings()
                cons = conn.get_all_concepts_with_embeddings()

            self._vector_cache = {m[0]: m[1] for m in mems}
            self._rebuild_matrix('_vector_cache', '_vector_matrix', '_vector_id_map')
            
            # 2. Load Concepts
            self._concept_cache = {c[0]: c[1] for c in cons}
            self._rebuild_matrix('_concept_cache', '_concept_matrix', '_concept_id_map')
            
            log.info(f"Caches loaded. Memories: {len(self._vector_id_map)}, Concepts: {len(self._concept_id_map)}")

    def _rebuild_matrix(self, cache_name, matrix_name, map_name):
        """Helper to rebuild a specific numpy matrix from a dict."""
        cache = getattr(self, cache_name)
        if not cache:
            setattr(self, matrix_name, None)
            setattr(self, map_name, [])
            return

        ids, vecs = zip(*cache.items())
        matrix = np.vstack(vecs).astype(np.float32)
        setattr(self, matrix_name, matrix)
        setattr(self, map_name, list(ids))

    # --- INPUT API ---

    def add_observation(self, data: Any, source: str = "unknown"):
        self.stm.add({"data": data, "source": source, "timestamp": datetime.now()})

    def get_and_clear_observations(self) -> List[Dict]:
        return self.stm.get_all_and_clear()

    def store_memory(self, content: str, content_type: str='observation', metadata: dict=None) -> int:
        embedding = self.compressor.embed(content)
        with self.ltm as conn:
            mid = conn.add_memory_with_embedding(content, embedding, content_type, self.compressor.model_name, metadata)
        
        with self._cache_lock:
            self._vector_cache[mid] = embedding
            self._rebuild_matrix('_vector_cache', '_vector_matrix', '_vector_id_map')
        return mid

    def add_symbolic_fact(self, subject, predicate, object_val, context=None):
        with self.ltm as conn:
            return conn.add_fact(subject, predicate, object_val, context)

    # --- NEW: CONCEPT API ---

    def create_concept(self, name: str, definition: str, embedding: np.ndarray) -> int:
        """
        Creates a concept in LTM and updates the Concept Vector Cache.
        """
        with self.ltm as conn:
            cid = conn.create_concept(name, definition, embedding)
        
        # If creation successful (or retrieved existing), update cache
        if cid > 0:
            with self._cache_lock:
                self._concept_cache[cid] = embedding
                self._rebuild_matrix('_concept_cache', '_concept_matrix', '_concept_id_map')
        return cid

    # --- RETRIEVAL API ---

    def find_relevant_memories(self, query: str, k=5, min_similarity=0.4):
        return self._search_index(query, '_vector_matrix', '_vector_id_map', self.ltm.get_memory_by_id, k, min_similarity)

    def find_relevant_concepts(self, query: str, k=3, min_similarity=0.5):
        """
        Finds concepts conceptually similar to the query.
        """
        return self._search_index(query, '_concept_matrix', '_concept_id_map', self.ltm.get_concept_by_id, k, min_similarity)

    def _search_index(self, query, matrix_attr, map_attr, fetch_func, k, min_sim):
        """Generic vector search logic."""
        q_vec = self.compressor.embed(query)
        matrix = getattr(self, matrix_attr)
        id_map = getattr(self, map_attr)

        with self._cache_lock:
            if matrix is None or matrix.shape[0] == 0:
                return []
            
            sims = np.dot(matrix, q_vec)
            top_idxs = np.argsort(sims)[-k:][::-1]
            
            results = []
            for idx in top_idxs:
                score = float(sims[idx])
                if score < min_sim: continue
                
                real_id = id_map[idx]
                data = fetch_func(real_id)
                if data:
                    results.append((dict(data), score))
            return results
        
    def perform_sleep_maintenance(self) -> int:
        """
        Runs the biological cleanup process.
        """
        log.info("Entering REM sleep... optimizing memory.")
        
        # 1. Prune unused memories (Aggressive: delete anything never accessed)
        # In a real app, you'd use a timestamp threshold.
        deleted_count = self.ltm.prune_memories(days_unused=0)
        
        # 2. Rebuild caches immediately to reflect the smaller DB
        self._load_caches()
        
        return deleted_count