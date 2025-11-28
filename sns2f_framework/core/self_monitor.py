# sns2f_framework/core/self_monitor.py

import time
import logging
from datetime import timedelta
from sns2f_framework.memory.memory_manager import MemoryManager

log = logging.getLogger(__name__)

class SelfMonitor:
    """
    The Metacognition Module.
    Allows the AI to introspect its own state, memory size, and uptime.
    """

    def __init__(self, memory_manager: MemoryManager):
        self.mm = memory_manager
        self.boot_time = time.time()

    def get_system_report(self) -> str:
        """
        Generates a natural language summary of the system's current state.
        Used to inject 'Self-Knowledge' into the prompt.
        """
        # 1. Gather Stats
        uptime = str(timedelta(seconds=int(time.time() - self.boot_time)))
        
        with self.mm.ltm as conn:
            # We access the raw connection to run count queries
            # (Using a private helper for cleaner code access)
            c = conn._get_connection()
            
            mem_count = c.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            concept_count = c.execute("SELECT COUNT(*) FROM concepts").fetchone()[0]
            fact_count = c.execute("SELECT COUNT(*) FROM symbolic_knowledge").fetchone()[0]
            
        # 2. Format the Report
        report = (
            f"--- IDENTITY: TURIYA ---\n"
            f"I am Turiya, a Self-Evolving Neuro-Symbolic Swarm.\n"
            f"Current Status: Online\n"
            f"Uptime: {uptime}\n"
            f"--- KNOWLEDGE BASE ---\n"
            f"Total Memories Read: {mem_count}\n"
            f"Synthesized Concepts: {concept_count}\n"
            f"Logic Facts Extracted: {fact_count}\n"
            f"Architecture: Hybrid (Vector + Graph)\n"
        )
        return report