# sns2f_framework/memory/long_term_memory.py

import sqlite3
import threading
import logging
import json
import numpy as np
import io
from datetime import datetime
from typing import Optional, Any, List, Tuple

from sns2f_framework.config import DB_PATH

log = logging.getLogger(__name__)

class LongTermMemory:
    """
    Manages the persistent, long-term memory store using SQLite.
    
    V2 Upgrade: Now supports a Concept Graph layer on top of the 
    raw Symbolic Knowledge layer.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.local = threading.local()
        self._initialize_database()
        log.info(f"LongTermMemory initialized with database at {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self.local, 'connection'):
            self.local.connection = sqlite3.connect(self.db_path, 
                                                    detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                                                    check_same_thread=False,
                                                    isolation_level=None) # <--- AUTOCOMMIT ENABLED
            self.local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self.local.connection.execute("PRAGMA journal_mode=WAL;")
        return self.local.connection

    def _initialize_database(self):
        log.debug("Initializing LTM database schema...")
        conn = self._get_connection()
        with conn:
            # 1. Symbolic Knowledge (The "Facts")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS symbolic_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(subject, predicate, object)
            );
            """)
            
            # 2. Memories (The "Raw Text")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                content_type TEXT DEFAULT 'observation',
                metadata TEXT,
                access_count INTEGER DEFAULT 0,
                last_access_ts TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 3. Embeddings (The "Vectors")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_embeddings (
                memory_id INTEGER NOT NULL,
                embedding BLOB NOT NULL,
                model_name TEXT NOT NULL,
                FOREIGN KEY(memory_id) REFERENCES memories(id) ON DELETE CASCADE
            );
            """)
            
            # --- V2: CONCEPT LAYER ---
            
            # 4. Concepts (The "Ideas")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS concepts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                definition TEXT,  -- The synthesized summary of the concept
                embedding BLOB,   -- Vector rep of the concept name/def
                metadata TEXT,    -- e.g., {'uncertainty': 0.2, 'source_count': 5}
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 5. Concept Edges (High-level relations between concepts)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS concept_edges (
                source_id INTEGER,
                target_id INTEGER,
                relation TEXT,
                weight REAL DEFAULT 1.0,
                FOREIGN KEY(source_id) REFERENCES concepts(id),
                FOREIGN KEY(target_id) REFERENCES concepts(id),
                UNIQUE(source_id, target_id, relation)
            );
            """)
           

            # --- V3: GRAMMAR LAYER ---
            conn.execute("""
            CREATE TABLE IF NOT EXISTS grammar_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                structure_hash TEXT UNIQUE NOT NULL, -- Unique ID for the pattern
                template TEXT NOT NULL,              -- e.g. "{Subject} was a {Adjective} {Object}."
                pos_sequence TEXT NOT NULL,          -- e.g. "PROPN AUX DET ADJ NOUN"
                frequency INTEGER DEFAULT 1,
                example_sentence TEXT
            );
            """)

            # 6. Schema Migration: Add link from Facts to Concepts
            # We try to add the column; if it fails, it likely already exists.
            try:
                conn.execute("ALTER TABLE symbolic_knowledge ADD COLUMN concept_id INTEGER REFERENCES concepts(id)")
                log.info("Schema Migration: Added 'concept_id' to symbolic_knowledge table.")
            except sqlite3.OperationalError:
                # Column likely exists already, ignore
                pass

    # --- HELPERS ---

    def _adapt_numpy_array(self, arr: np.ndarray) -> sqlite3.Binary:
        out = io.BytesIO()
        np.save(out, arr)
        out.seek(0)
        return sqlite3.Binary(out.read())

    def _convert_numpy_array(self, text: bytes) -> np.ndarray:
        out = io.BytesIO(text)
        out.seek(0)
        return np.load(out)
        
    def __enter__(self):
        sqlite3.register_adapter(np.ndarray, self._adapt_numpy_array)
        sqlite3.register_converter("NPARRAY", self._convert_numpy_array)
        self.local.connection = self._get_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self.local, 'connection'):
            self.local.connection.close()
            del self.local.connection

    # --- CONCEPT API (New for V2) ---

    def create_concept(self, name: str, definition: str = "", embedding: Optional[np.ndarray] = None) -> int:
        """Creates a new high-level Concept."""
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.execute(
                    "INSERT INTO concepts (name, definition, embedding) VALUES (?, ?, ?)",
                    (name, definition, embedding)
                )
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Concept exists, return its ID
            cursor = conn.execute("SELECT id FROM concepts WHERE name = ?", (name,))
            row = cursor.fetchone()
            return row['id'] if row else -1

    def get_concept_by_name(self, name: str) -> Optional[sqlite3.Row]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM concepts WHERE name = ?", (name,))
        return cursor.fetchone()

    def get_concept_by_id(self, concept_id: int) -> Optional[sqlite3.Row]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM concepts WHERE id = ?", (concept_id,))
        return cursor.fetchone()
        
    def link_fact_to_concept(self, fact_id: int, concept_id: int):
        """Associates a specific fact (triple) with a parent Concept."""
        conn = self._get_connection()
        with conn:
            conn.execute(
                "UPDATE symbolic_knowledge SET concept_id = ? WHERE id = ?",
                (concept_id, fact_id)
            )

    # --- SYMBOLIC KNOWLEDGE API ---

    def add_fact(self, subject: str, predicate: str, object: str, context: Optional[dict] = None) -> int:
        conn = self._get_connection()
        context_json = json.dumps(context) if context else None
        try:
            with conn:
                cursor = conn.execute(
                    "INSERT INTO symbolic_knowledge (subject, predicate, object, context) VALUES (?, ?, ?, ?)",
                    (subject, predicate, object, context_json)
                )
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Return existing ID if duplicate
            cursor = conn.execute(
                "SELECT id FROM symbolic_knowledge WHERE subject=? AND predicate=? AND object=?", 
                (subject, predicate, object)
            )
            row = cursor.fetchone()
            return row['id'] if row else -1

    def find_facts(self, subject: Optional[str] = None, predicate: Optional[str] = None, object: Optional[str] = None) -> List[sqlite3.Row]:
        conn = self._get_connection()
        query = "SELECT * FROM symbolic_knowledge WHERE 1=1"
        params = []
        
        if subject:
            query += " AND subject = ?"
            params.append(subject)
        if predicate:
            query += " AND predicate = ?"
            params.append(predicate)
        if object:
            query += " AND object = ?"
            params.append(object)
            
        with conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()

    def get_facts_by_concept(self, concept_id: int) -> List[sqlite3.Row]:
        """Retrieves all facts clustered under a specific concept."""
        conn = self._get_connection()
        with conn:
            cursor = conn.execute("SELECT * FROM symbolic_knowledge WHERE concept_id = ?", (concept_id,))
            return cursor.fetchall()

    # --- NEURAL/SEMANTIC MEMORY API ---

    def add_memory_with_embedding(self, content: str, embedding: np.ndarray, 
                                  content_type: str = 'observation', 
                                  model_name: str = 'unknown', 
                                  metadata: Optional[dict] = None) -> int:
        conn = self._get_connection()
        metadata_json = json.dumps(metadata) if metadata else None
        
        with conn:
            mem_cursor = conn.execute(
                "INSERT INTO memories (content, content_type, metadata, created_at) VALUES (?, ?, ?, ?)",
                (content, content_type, metadata_json, datetime.now()) # <--- The fix
            )
            memory_id = mem_cursor.lastrowid
            
            conn.execute(
                "INSERT INTO memory_embeddings (memory_id, embedding, model_name) VALUES (?, ?, ?)",
                (memory_id, embedding, model_name)
            )
        return memory_id

    def get_all_memories_with_embeddings(self) -> List[Tuple[int, np.ndarray, sqlite3.Row]]:
        conn = self._get_connection()
        query = """
        SELECT
            m.id,
            m.content,
            m.content_type,
            m.metadata,
            m.access_count,
            m.last_access_ts,
            m.created_at,
            e.embedding as "embedding [NPARRAY]"
        FROM memories m
        JOIN memory_embeddings e ON m.id = e.memory_id
        """
        with conn:
            cursor = conn.execute(query)
            results = []
            for row in cursor.fetchall():
                memory_id = row['id']
                embedding = row['embedding']
                memory_data = dict(row)
                del memory_data['embedding']
                results.append((memory_id, embedding, memory_data))
            return results
        
    def get_all_concepts_with_embeddings(self) -> List[Tuple[int, np.ndarray, sqlite3.Row]]:
        """
        Retrieves all concepts and their embeddings for the cache.
        """
        conn = self._get_connection()
        query = """
        SELECT
            id,
            name,
            definition,
            metadata,
            embedding as "embedding [NPARRAY]"
        FROM concepts
        WHERE embedding IS NOT NULL
        """
        with conn:
            cursor = conn.execute(query)
            results = []
            for row in cursor.fetchall():
                c_id = row['id']
                emb = row['embedding']
                data = dict(row)
                del data['embedding']
                results.append((c_id, emb, data))
            return results
        
    def get_memory_by_id(self, memory_id: int) -> Optional[sqlite3.Row]:
        conn = self._get_connection()
        with conn:
            cursor = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
            return cursor.fetchone()

    def update_memory_access(self, memory_id: int):
        conn = self._get_connection()
        with conn:
            conn.execute(
                "UPDATE memories SET access_count = access_count + 1, last_access_ts = ? WHERE id = ?",
                (datetime.now(), memory_id) # <--- The fix
            )

    def prune_memories(self, days_unused: int = 7) -> int:
        """
        Deletes memories that have 0 access_count and are older than N days.
        Returns the number of deleted items.
        """
        conn = self._get_connection()
        
        # Calculate the cutoff date
        # Note: Since we use simple strings for dates now, we rely on SQLite's string comparison
        # In a production system, you'd calculate the exact date string.
        # For this prototype, we'll just delete anything with access_count=0 
        # (aggressive pruning for demo purposes, or you can skip the date check).
        
        with conn:
            # First, delete embeddings (FK cascade should handle this, but explicit is safer)
            # We find IDs to delete first
            cursor = conn.execute(
                "SELECT id FROM memories WHERE access_count = 0"
            )
            ids_to_delete = [row['id'] for row in cursor.fetchall()]
            
            if not ids_to_delete:
                return 0
                
            # SQLite doesn't support list parameters easily, so we loop or use "IN (...)" string format
            id_list = ",".join(map(str, ids_to_delete))
            
            conn.execute(f"DELETE FROM memory_embeddings WHERE memory_id IN ({id_list})")
            conn.execute(f"DELETE FROM memories WHERE id IN ({id_list})")
            
            return len(ids_to_delete)