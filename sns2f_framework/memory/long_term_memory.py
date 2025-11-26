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
    
    This class handles two primary forms of knowledge:
    1.  Symbolic Knowledge: Stored as (subject, predicate, object) triples in a graph.
    2.  Episodic/Semantic Memories: Stored as text chunks with associated metadata
        and a neural vector embedding for similarity search.
        
    It is designed to be thread-safe for a multi-agent environment.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        # Use a thread-local connection object
        self.local = threading.local()
        self._initialize_database()
        log.info(f"LongTermMemory initialized with database at {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """
        Gets a thread-local database connection.
        """
        if not hasattr(self.local, 'connection'):
            self.local.connection = sqlite3.connect(self.db_path, 
                                                    detect_types=sqlite3.PARSE_DECLTYPES,
                                                    check_same_thread=False) # We handle our own threading
            self.local.connection.row_factory = sqlite3.Row
        return self.local.connection

    def _initialize_database(self):
        """
        Creates all necessary tables if they don't already exist.
        """
        log.debug("Initializing LTM database schema...")
        conn = self._get_connection()
        with conn:
            # --- Symbolic Knowledge Graph Table ---
            conn.execute("""
            CREATE TABLE IF NOT EXISTS symbolic_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                context TEXT, -- JSON blob for metadata (e.g., source, certainty)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(subject, predicate, object)
            );
            """)
            log.debug("Table 'symbolic_knowledge' is ready.")
            
            # --- Episodic/Semantic Memory Table ---
            conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                content_type TEXT DEFAULT 'observation', -- e.g., 'summary', 'raw_text', 'fact'
                metadata TEXT, -- JSON blob (source_url, timestamps, etc.)
                access_count INTEGER DEFAULT 0,
                last_access_ts TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            log.debug("Table 'memories' is ready.")

            # --- Neural Embeddings Table ---
            # This stores the vector representation of a memory
            conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_embeddings (
                memory_id INTEGER NOT NULL,
                embedding BLOB NOT NULL,
                model_name TEXT NOT NULL, -- Track which model generated this
                FOREIGN KEY(memory_id) REFERENCES memories(id) ON DELETE CASCADE
            );
            """)
            log.debug("Table 'memory_embeddings' is ready.")

    # --- HELPER METHODS for data conversion ---

    def _adapt_numpy_array(self, arr: np.ndarray) -> sqlite3.Binary:
        """Converts numpy array to BLOB for SQLite."""
        out = io.BytesIO()
        np.save(out, arr)
        out.seek(0)
        return sqlite3.Binary(out.read())

    def _convert_numpy_array(self, text: bytes) -> np.ndarray:
        """Converts BLOB from SQLite back to numpy array."""
        out = io.BytesIO(text)
        out.seek(0)
        return np.load(out)
        
    def __enter__(self):
        # Register the numpy array adapters for this connection
        sqlite3.register_adapter(np.ndarray, self._adapt_numpy_array)
        sqlite3.register_converter("NPARRAY", self._convert_numpy_array)
        self.local.connection = self._get_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self.local, 'connection'):
            self.local.connection.close()
            del self.local.connection

    # --- SYMBOLIC KNOWLEDGE API ---

    def add_fact(self, subject: str, predicate: str, object: str, context: Optional[dict] = None) -> int:
        """
        Adds a new symbolic fact (triple) to the knowledge graph.
        """
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
            log.warning(f"Fact ({subject}, {predicate}, {object}) already exists.")
            return -1 # Indicate failure due to uniqueness constraint

    def find_facts(self, subject: Optional[str] = None, predicate: Optional[str] = None, object: Optional[str] = None) -> List[sqlite3.Row]:
        """
        Queries the knowledge graph.
        e.g., find_facts(subject="SNS2F", predicate="is_a")
        """
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

    # --- NEURAL/SEMANTIC MEMORY API ---

    def add_memory_with_embedding(self, content: str, embedding: np.ndarray, 
                                  content_type: str = 'observation', 
                                  model_name: str = 'unknown', 
                                  metadata: Optional[dict] = None) -> int:
        """
        Adds a new memory and its associated embedding in a single transaction.
        """
        conn = self._get_connection()
        metadata_json = json.dumps(metadata) if metadata else None
        
        with conn:
            # 1. Insert the memory content
            mem_cursor = conn.execute(
                "INSERT INTO memories (content, content_type, metadata, created_at) VALUES (?, ?, ?, ?)",
                (content, content_type, metadata_json, datetime.now())
            )
            memory_id = mem_cursor.lastrowid
            
            # 2. Insert the embedding
            conn.execute(
                "INSERT INTO memory_embeddings (memory_id, embedding, model_name) VALUES (?, ?, ?)",
                (memory_id, embedding, model_name)
            )
        
        log.debug(f"Stored new memory (ID: {memory_id}) with embedding.")
        return memory_id

    def get_all_memories_with_embeddings(self) -> List[Tuple[int, np.ndarray, sqlite3.Row]]:
        """
        Retrieves all memories and their embeddings.
        Used to load the vector cache for the neural reasoning engine.
        
        Returns:
            A list of (memory_id, embedding, memory_row)
        """
        conn = self._get_connection()
        # Declare the 'NPARRAY' converter for this query
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
            # Re-package the row to be more intuitive
            results = []
            for row in cursor.fetchall():
                memory_id = row['id']
                embedding = row['embedding']
                # Create a new dictionary for the memory data, excluding the blob
                memory_data = dict(row)
                del memory_data['embedding']
                
                results.append((memory_id, embedding, memory_data))
            return results
        
    def get_memory_by_id(self, memory_id: int) -> Optional[sqlite3.Row]:
        """
        Retrieves a single memory's content and metadata by its primary ID.
        """
        conn = self._get_connection()
        with conn:
            cursor = conn.execute(
                "SELECT * FROM memories WHERE id = ?",
                (memory_id,)
            )
            return cursor.fetchone()
        
    def update_memory_access(self, memory_id: int):
        """
OPEN_ENDED
Updates the access count and timestamp for a memory.
        """
        conn = self._get_connection()
        with conn:
            conn.execute(
                "UPDATE memories SET access_count = access_count + 1, last_access_ts = ? WHERE id = ?",
                (datetime.now(), memory_id)
            )