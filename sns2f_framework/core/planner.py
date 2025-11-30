# sns2f_framework/core/planner.py

import logging
import re
from typing import List, Optional, Dict, Any

log = logging.getLogger(__name__)

class Planner:
    """
    Executive Function.
    Decomposes high-level intents into sequences of atomic queries.
    """

    def __init__(self):
        # The "Recipe Book"
        self.plans = {
            "biography": [
                "Who is {topic}?",
                "When was {topic} born?",
                "What did {topic} do?",
                "When did {topic} die?"
            ],
            "analysis": [
                "Define {topic}.",
                "What is {topic} used for?",
                "How is {topic} related to technology?"
            ],
            "history": [
                "What is {topic}?",
                "When did {topic} happen?",
                "Who was involved in {topic}?"
            ]
        }

    def generate_plan(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Analyzes input to see if it matches a complex plan.
        Returns: {'type': 'biography', 'steps': ['query1', 'query2'...]}
        """
        text_lower = text.lower()
        
        # 1. Biography Trigger
        # Matches: "biography of X", "life of X", "tell me about X"
        if "biography of" in text_lower or "life of" in text_lower or "tell me about" in text_lower:
            topic = self._extract_topic(text, ["biography of", "life of", "tell me about"])
            return {
                "type": "biography",
                "steps": [step.format(topic=topic) for step in self.plans["biography"]]
            }

        # 2. Deep Dive / Analysis Trigger
        if "analyze" in text_lower or "deep dive" in text_lower:
            topic = self._extract_topic(text, ["analyze", "deep dive into", "deep dive"])
            return {
                "type": "analysis",
                "steps": [step.format(topic=topic) for step in self.plans["analysis"]]
            }

        return None

    def _extract_topic(self, text: str, triggers: List[str]) -> str:
        """Helper to strip the trigger phrase and get the noun."""
        for t in triggers:
            if t in text.lower():
                # Split on the trigger, take the part after it
                # e.g. "biography of [Alan Turing]"
                parts = re.split(t, text, flags=re.IGNORECASE)
                if len(parts) > 1:
                    return parts[1].strip("?. ")
        return text # Fallback