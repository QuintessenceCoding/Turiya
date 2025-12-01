# sns2f_framework/reasoning/generalizer.py

import logging
import sqlite3
from typing import List, Any

log = logging.getLogger(__name__)

class Generalizer:
    """
    The Abstraction Engine.
    Runs during Sleep. Finds patterns in facts and creates Super-Concepts.
    """

    def __init__(self, memory_manager, llm_callable):
        self.mm = memory_manager
        self.llm_func = llm_callable
        # How many items must share a property to trigger abstraction?
        self.cluster_threshold = 3 

    def run(self) -> int:
        log.info("🧠 Starting Generalization Cycle...")
        
        # 1. Find Clusters
        clusters = self._find_shared_properties()
        
        new_abstractions = 0
        
        for prop, subjects in clusters.items():
            predicate, obj = prop
            
            # Don't abstract generic things like "is a" -> "noun"
            if predicate in ["is", "are", "be"] and len(obj) < 4:
                continue

            log.info(f"Found cluster: {len(subjects)} items {predicate} {obj}")
            
            # 2. Name the Category (using LLM)
            category_name = self._name_the_category(subjects, predicate, obj)
            
            if category_name and "unknown" not in category_name.lower():
                # 3. Create the Super-Concept
                self._crystallize_category(category_name, subjects, predicate, obj)
                new_abstractions += 1

        return new_abstractions

    def _find_shared_properties(self) -> dict:
        """
        SQL Magic: Group by P and O, count S.
        """
        with self.mm.ltm as ltm_wrapper:
            # FIX: Access the raw connection explicitly
            db = ltm_wrapper._get_connection()
            
            cursor = db.execute(f"""
                SELECT predicate, object, GROUP_CONCAT(subject, '|') as subjects, COUNT(*) as cnt
                FROM symbolic_knowledge
                GROUP BY predicate, object
                HAVING cnt >= {self.cluster_threshold}
                ORDER BY cnt DESC
                LIMIT 5
            """)
            
            clusters = {}
            for row in cursor.fetchall():
                subjects = list(set(row['subjects'].split('|')))
                if len(subjects) >= self.cluster_threshold:
                    clusters[(row['predicate'], row['object'])] = subjects
            
            return clusters

    def _name_the_category(self, subjects: List[str], predicate: str, obj: str) -> str:
        subject_list = ", ".join(subjects[:5])
        
        prompt = (
            f"<|system|>\n"
            f"You are a taxonomy expert. Group these items into a single category name.\n"
            f"Items: {subject_list}\n"
            f"Shared Property: They all {predicate} {obj}.\n"
            f"Task: Return ONE word or short phrase representing this category (e.g., 'Carnivores', 'Planets').\n"
            f"Category Name:\n"
            f"<|assistant|>\n"
        )
        
        try:
            output = self.llm_func(prompt, max_tokens=10, stop=["\n"], echo=False)
            category = output['choices'][0]['text'].strip().strip(".\"")
            log.info(f"Generalizer suggests category: '{category}'")
            return category
        except Exception as e:
            log.error(f"Generalizer LLM failed: {e}")
            return None

    def _crystallize_category(self, category: str, subjects: List[str], pred: str, obj: str):
        """
        Creates the Concept and links the children.
        """
        # 1. Create the Super-Concept
        def_text = f"{category} is a group containing {', '.join(subjects[:3])}, defined by {pred} {obj}."
        embedding = self.mm.compressor.embed(def_text)
        
        cat_id = self.mm.create_concept(category, def_text, embedding)
        
        if cat_id > 0:
            # 2. Link Children to Parent (Taxonomy)
            with self.mm.ltm as ltm_wrapper:
                # FIX: Access raw connection
                db = ltm_wrapper._get_connection()
                
                for subj in subjects:
                    # Add fact: (Lion, is a, Carnivore)
                    try:
                        db.execute(
                            "INSERT OR IGNORE INTO symbolic_knowledge (subject, predicate, object, context) VALUES (?, ?, ?, ?)",
                            (subj, "is a", category, '{"source": "generalizer"}')
                        )
                        
                        # Add Concept Edge (Graph Layer)
                        subj_row = db.execute("SELECT id FROM concepts WHERE name = ?", (subj,)).fetchone()
                        if subj_row:
                            db.execute(
                                "INSERT OR IGNORE INTO concept_edges (source_id, target_id, relation) VALUES (?, ?, ?)",
                                (subj_row['id'], cat_id, "child_of")
                            )
                    except sqlite3.Error as e:
                        log.warning(f"Generalizer DB error: {e}")