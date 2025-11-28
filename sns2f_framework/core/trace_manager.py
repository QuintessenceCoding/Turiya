# sns2f_framework/core/trace_manager.py

import logging
import threading
import time
from collections import defaultdict
from typing import List, Dict, Optional

log = logging.getLogger(__name__)

class TraceManager:
    """
    The 'Stream of Consciousness' Recorder.
    It tracks the lifecycle of a specific user query across all agents.
    """
    
    def __init__(self):
        # Structure: { request_id: [ {time, agent, action, detail} ] }
        self._traces: Dict[str, List[dict]] = defaultdict(list)
        self._lock = threading.Lock()

    def record(self, request_id: Optional[str], agent_name: str, action: str, detail: str = ""):
        """
        Log a specific cognitive step.
        If request_id is None, it's a general system event (not attached to a specific user query).
        """
        if not request_id: 
            return
        
        entry = {
            "time": time.strftime("%H:%M:%S"),
            "agent": agent_name,
            "action": action,
            "detail": detail
        }
        
        with self._lock:
            self._traces[request_id].append(entry)

    def get_trace(self, request_id: str) -> str:
        """
        Formats the trace into a readable report.
        """
        with self._lock:
            steps = self._traces.get(request_id, [])
        
        if not steps:
            return f"No trace found for ID: {request_id}"

        report = [f"\n🧠 THOUGHT TRACE [ID: {request_id[:8]}...]"]
        report.append("=" * 65)
        
        for i, step in enumerate(steps, 1):
            # Dynamic icons for visual parsing
            icon = "🔹"
            if "Reasoning" in step['agent']: icon = "🤔"
            elif "Perception" in step['agent']: icon = "👀"
            elif "Learning" in step['agent']: icon = "💾"
            elif "Orchestrator" in step['agent']: icon = "🎮"
            
            # Format: 1. 10:00:00 [Agent] Action
            line = f"{i}. {step['time']} {icon} [{step['agent']}] {step['action']}"
            if step['detail']:
                # Indent detail
                line += f"\n    └─ {step['detail']}"
            report.append(line)
            
        report.append("=" * 65)
        return "\n".join(report)

# Singleton instance
trace_manager = TraceManager()