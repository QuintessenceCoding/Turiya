# sns2f_framework/reasoning/concept_miner.py

import logging
import sqlite3
from typing import List, Any, Dict

from sns2f_framework.memory.memory_manager import MemoryManager

log = logging.getLogger(__name__)

class ConceptMiner:
    """
    The 'Librarian' of the swarm.
    
    It scans the raw Symbolic Knowledge graph for patterns.
    If a subject appears frequently (is 'dense'), this miner:
    1. Promotes it to a high-level Concept.
    2. Synthesizes a definition using the LLM.
    3. Links the raw facts to the new Concept.
    """

    def __init__(self, memory_manager: MemoryManager, llm_callable: Any):
        self.mm = memory_manager
        self.llm = llm_callable
        self.min_frequency = 2  # Low threshold for testing, increase for prod

    def run_mining_cycle(self) -> int:
        """
        Main execution loop. Returns number of new concepts created.
        """
        log.info("Starting Concept Mining cycle...")
        
        # 1. Find candidates
        candidates = self._find_unlinked_candidates()
        if not candidates:
            log.info("No new concepts to mine.")
            return 0

        created_count = 0
        
        for subject, count in candidates:
            log.info(f"Crystallizing concept: '{subject}' ({count} facts)")
            
            # 2. Gather facts
            facts = self._get_facts_for_subject(subject)
            fact_texts = [f"{row['subject']} {row['predicate']} {row['object']}" for row in facts]
            
            # 3. Generate Definition (Neuro-Symbolic Synthesis)
            definition = self._synthesize_definition(subject, fact_texts)
            
            # 4. Create Concept Node
            # We use the neural compressor to embed the definition for semantic search later
            def_embedding = self.mm.compressor.embed(f"{subject}: {definition}")
            
            concept_id = self.mm.create_concept(
                name=subject,
                definition=definition,
                embedding=def_embedding
            )
            
            # 5. Link Facts to Concept
            if concept_id > 0:
                self._link_facts(facts, concept_id)
                created_count += 1
                
        log.info(f"Mining complete. Created {created_count} new concepts.")
        return created_count

    def _find_unlinked_candidates(self) -> List[tuple]:
        """
        SQL Query to find subjects that have > N facts but NO concept_id.
        """
        query = """
        SELECT subject, COUNT(*) as cnt 
        FROM symbolic_knowledge 
        WHERE concept_id IS NULL 
        GROUP BY subject 
        HAVING cnt >= ?
        """
        # We need direct access to run this analytic query
        with self.mm.ltm as conn:
            # Note: We must access the underlying connection object from the wrapper
            cursor = conn._get_connection().execute(query, (self.min_frequency,))
            return [(row['subject'], row['cnt']) for row in cursor.fetchall()]

    def _get_facts_for_subject(self, subject: str) -> List[sqlite3.Row]:
        with self.mm.ltm as conn:
            return conn.find_facts(subject=subject)

    def _link_facts(self, facts: List[sqlite3.Row], concept_id: int):
        with self.mm.ltm as conn:
            for row in facts:
                conn.link_fact_to_concept(row['id'], concept_id)

    def _synthesize_definition(self, subject: str, facts: List[str]) -> str:
        """
        Uses the LLM to write a dictionary definition based ONLY on the known facts.
        """
        if not self.llm:
            return f"A concept related to {facts[0] if facts else 'unknown'}."

        facts_block = "\n".join([f"- {f}" for f in facts])
        
        prompt = (
            f"<|system|>\n"
            f"You are a lexicographer. Write a single, concise definition sentence for '{subject}'. "
            f"Use ONLY the facts provided below. Do not add outside knowledge.\n"
            f"Facts:\n{facts_block}</s>\n"
            f"<|user|>\n"
            f"Define '{subject}':</s>\n"
            f"<|assistant|>\n"
        )

        try:
            output = self.llm(
                prompt,
                max_tokens=60,
                stop=["</s>", "\n"],
                echo=False,
                temperature=0.1
            )
            return output['choices'][0]['text'].strip()
        except Exception as e:
            log.error(f"Def synthesis failed for {subject}: {e}")
            return "Definition unavailable."