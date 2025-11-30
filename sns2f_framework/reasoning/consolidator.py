# sns2f_framework/reasoning/consolidator.py

import logging
import sqlite3

log = logging.getLogger(__name__)

class Consolidator:
    """
    The Maintenance Engine.
    Runs during Sleep Cycle to clean, merge, and organize the Knowledge Graph.
    """

    def __init__(self, memory_manager):
        self.mm = memory_manager

    def run_sleep_cycle(self) -> dict:
        """
        Main entry point for sleep maintenance.
        """
        log.info("💤 Starting Sleep Cycle (Consolidation)...")
        stats = {
            "deleted_noise": 0,
            "merged_duplicates": 0,
            "concepts_formed": 0
        }

        # 1. Hygiene
        stats["deleted_noise"] = self._prune_noise()

        # 2. Deduplication
        stats["merged_duplicates"] = self._merge_duplicates()

        # 3. Concept Formation
        stats["concepts_formed"] = self._crystallize_dense_nodes()

        log.info(f"💤 Sleep complete. Stats: {stats}")
        return stats

    def _prune_noise(self) -> int:
        # Use context manager to ensure connection is open/valid
        with self.mm.ltm as conn:
            # We access the raw connection via the wrapper's helper
            # Note: The wrapper returns 'self' in __enter__, so we call _get_connection() on it
            db = conn._get_connection()
            
            delete_query = """
            DELETE FROM symbolic_knowledge 
            WHERE LENGTH(subject) < 2 
               OR LENGTH(object) < 2
               OR subject GLOB '[0-9]*'
               OR object LIKE '%http%'
            """
            cursor = db.execute(delete_query)
            return cursor.rowcount

    def _merge_duplicates(self) -> int:
        with self.mm.ltm as conn:
            db = conn._get_connection()
            query = """
            DELETE FROM symbolic_knowledge
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM symbolic_knowledge
                GROUP BY LOWER(subject), LOWER(predicate), LOWER(object)
            )
            """
            cursor = db.execute(query)
            return cursor.rowcount

    def _crystallize_dense_nodes(self) -> int:
        created = 0
        with self.mm.ltm as conn:
            db = conn._get_connection()
            
            # Find dense nodes
            rows = db.execute("""
                SELECT subject, COUNT(*) as cnt 
                FROM symbolic_knowledge 
                GROUP BY subject 
                HAVING cnt >= 5
            """).fetchall()

            for r in rows:
                subject = r['subject']
                
                # Check if concept exists
                exists = db.execute("SELECT 1 FROM concepts WHERE name = ?", (subject,)).fetchone()
                if not exists:
                    facts = db.execute(
                        "SELECT predicate, object FROM symbolic_knowledge WHERE subject = ? LIMIT 3", 
                        (subject,)
                    ).fetchall()
                    
                    if not facts: continue

                    # Synthesize definition
                    def_parts = [f"which {f['predicate']} {f['object']}" for f in facts]
                    definition = f"{subject} is an entity " + ", and ".join(def_parts) + "."
                    
                    # Embed
                    embedding = self.mm.compressor.embed(definition)
                    
                    # Create concept directly
                    db.execute(
                        "INSERT INTO concepts (name, definition, embedding) VALUES (?, ?, ?)",
                        (subject, definition, embedding)
                    )
                    created += 1
        
        return created