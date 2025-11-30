# sns2f_framework/reasoning/inference_engine.py

import logging
from typing import List, Tuple, Dict, Set

log = logging.getLogger(__name__)

class InferenceEngine:
    """
    The Logic Processor.
    Performs graph traversal to find connections between concepts.
    """

    def __init__(self, memory_manager):
        self.mm = memory_manager

    def find_connection(self, start_entity: str, end_entity: str, max_depth: int = 4) -> List[str]:
        """
        Finds a path between two entities using BFS (Breadth-First Search).
        Returns a list of sentences describing the path.
        """
        # 1. Get Start/End Identifiers (Fuzzy matching)
        start_facts = self._get_facts(start_entity)
        end_facts = self._get_facts(end_entity)
        
        if not start_facts or not end_facts:
            return ["I do not have enough data on one of these topics to connect them."]

        # We use the raw subject strings as nodes
        start_node = start_facts[0][0] # Best guess
        # For the target, we accept any known fact subject that matches the end_entity
        target_nodes = {f[0] for f in end_facts}

        # 2. BFS Pathfinding
        queue = [(start_node, [])] # (current_node, path_history)
        visited = set()

        log.info(f"Inferring path from '{start_node}' to '{end_entity}'...")

        while queue:
            current, path = queue.pop(0)
            
            if current in visited: continue
            visited.add(current)

            # Check if we reached the target
            if current in target_nodes or end_entity.lower() in current.lower():
                return self._format_path(path)

            if len(path) >= max_depth: continue

            # Get neighbors (facts where current node is the Subject)
            neighbors = self.mm.ltm.find_facts(subject=current)
            for row in neighbors:
                # The 'object' becomes the next node to visit
                next_node = row['object']
                step = (row['subject'], row['predicate'], row['object'])
                new_path = path + [step]
                queue.append((next_node, new_path))

        return ["No logical connection found within reasoning depth."]

    def _get_facts(self, entity: str):
        """Helper to get facts for fuzzy matching."""
        # Reuse the ReasoningAgent's logic, but simpler here
        with self.mm.ltm as conn:
            cursor = conn._get_connection().execute(
                "SELECT subject, predicate, object FROM symbolic_knowledge WHERE subject LIKE ? LIMIT 1",
                (f"%{entity}%",)
            )
            return cursor.fetchall()

    def _format_path(self, path: List[Tuple]) -> List[str]:
        """Converts a chain of triples into a narrative."""
        narrative = []
        for i, (s, p, o) in enumerate(path):
            if i == 0:
                narrative.append(f"{s} {p} {o}.")
            else:
                # Connector logic
                narrative.append(f"Processing '{s}', we find that it {p} {o}.")
        return narrative