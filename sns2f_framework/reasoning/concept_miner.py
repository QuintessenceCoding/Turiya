# sns2f_framework/reasoning/concept_miner.py

import logging
import sqlite3
from collections import defaultdict
from typing import List, Any

from sns2f_framework.memory.memory_manager import MemoryManager

log = logging.getLogger(__name__)

class ConceptMiner:
    """
    The Evolution Engine.
    Organizes raw facts into higher-order Concepts.
    V2: Now performs Synonym Merging (e.g. "Turing" == "Alan Turing").
    """

    def __init__(self, memory_manager: MemoryManager, llm_callable: Any = None):
        self.mm = memory_manager
        # No LLM needed for Symbolic V3
        self.min_frequency = 3 

    def run_mining_cycle(self) -> int:
        log.info("💎 Starting Concept Evolution Cycle...")
        
        # 1. Identify dense subjects
        candidates = self._find_dense_subjects()
        if not candidates:
            log.info("No dense clusters found.")
            return 0

        created_count = 0
        
        # 2. Merge Synonyms (Simple Heuristic)
        # Group "Alan Turing", "Turing", "A. M. Turing" together
        clusters = self._cluster_synonyms(candidates)
        
        for primary_name, aliases in clusters.items():
            log.info(f"Evolving Concept: '{primary_name}' (Merged: {aliases})")
            
            # 3. Create/Get Concept
            # Synthesize a definition from the facts
            all_facts = []
            for alias in aliases:
                facts = self._get_facts_for_subject(alias)
                all_facts.extend(facts)
            
            if not all_facts: continue

            # Create Definition
            definition = self._synthesize_definition(primary_name, all_facts)
            
            # Embed
            embedding = self.mm.compressor.embed(f"{primary_name}: {definition}")
            
            # Save Concept
            concept_id = self.mm.create_concept(primary_name, definition, embedding)
            
            # 4. Link Facts to this Concept
            if concept_id > 0:
                self._link_facts(all_facts, concept_id)
                created_count += 1
                
        log.info(f"Evolution complete. Evolved {created_count} concepts.")
        return created_count

    def _find_dense_subjects(self) -> List[str]:
        query = """
        SELECT subject, COUNT(*) as cnt 
        FROM symbolic_knowledge 
        WHERE concept_id IS NULL 
        GROUP BY subject 
        HAVING cnt >= ?
        """
        with self.mm.ltm as conn:
            cursor = conn._get_connection().execute(query, (self.min_frequency,))
            return [row['subject'] for row in cursor.fetchall()]

    def _cluster_synonyms(self, subjects: List[str]) -> dict:
        """
        Groups subjects that are likely the same entity.
        Logic: If 'Turing' is a substring of 'Alan Turing', group them.
        """
        clusters = defaultdict(list)
        sorted_subs = sorted(subjects, key=len, reverse=True) # Longest first
        
        assigned = set()
        
        for s1 in sorted_subs:
            if s1 in assigned: continue
            
            # Start a new cluster
            clusters[s1].append(s1)
            assigned.add(s1)
            
            # Find smaller substrings
            for s2 in sorted_subs:
                if s2 in assigned: continue
                
                # Check overlap (Simple containment)
                # e.g. "Turing" in "Alan Turing"
                if s2 in s1 or s1 in s2:
                    clusters[s1].append(s2)
                    assigned.add(s2)
                    
        return clusters

    def _get_facts_for_subject(self, subject: str) -> List[sqlite3.Row]:
        with self.mm.ltm as conn:
            return conn.find_facts(subject=subject)

    def _link_facts(self, facts: List[sqlite3.Row], concept_id: int):
        with self.mm.ltm as conn:
            for row in facts:
                conn.link_fact_to_concept(row['id'], concept_id)

    def _synthesize_definition(self, subject: str, facts: List[sqlite3.Row]) -> str:
        """
        Constructs a definition string from the 'is_a' facts.
        """
        # Find defining predicates
        definitions = []
        for f in facts:
            if f['predicate'] in ["is", "be", "is a", "was", "implies"]:
                definitions.append(f['object'])
        
        if definitions:
            # Take top 2 definitions
            desc = ", ".join(definitions[:2])
            return f"{subject} is defined as {desc}."
        
        # Fallback
        return f"{subject} is an entity associated with {facts[0]['object']}."