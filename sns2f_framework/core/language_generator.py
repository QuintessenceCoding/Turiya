# sns2f_framework/core/language_generator.py

import random
import re
import logging
from typing import Dict, List, Any

log = logging.getLogger(__name__)

class LanguageGenerator:
    """
    Layer 4: Language Realization.
    V5.1: The Complete Engine.
    Features:
    - Learned Templates (Grammar Induction)
    - Verb Conjugation (Morphology)
    - Relevance Sorting (Quality Control)
    """
    
    def __init__(self, memory_manager=None):
        self.mm = memory_manager
        
        # 1. Innate Templates
        self.templates = {
            "definition": [
                "{subject} is {object}.",
                "{subject} is defined as {object}.",
                "Records show {subject} {predicate} {object}."
            ],
            "fact": [
                "{subject} {predicate} {object}.",
                "{subject} also {predicate} {object}.",
                "It is known that {subject} {predicate} {object}."
            ],
            "unknown": [
                "I do not have enough data to define '{target}' yet.",
                "My knowledge graph is missing: '{target}'. I will search."
            ]
        }

        # 2. Irregular Verb Map
        self.irregular_verbs = {
            "be": "was", "have": "had", "do": "did", "say": "said", "go": "went",
            "get": "got", "make": "made", "know": "knew", "think": "thought",
            "take": "took", "see": "saw", "come": "came", "find": "found",
            "give": "gave", "tell": "told", "become": "became", "show": "showed",
            "leave": "left", "feel": "felt", "bring": "brought", "begin": "began",
            "keep": "kept", "hold": "held", "write": "wrote", "stand": "stood",
            "hear": "heard", "let": "let", "mean": "meant", "set": "set",
            "meet": "met", "run": "ran", "pay": "paid", "sit": "sat",
            "speak": "spoke", "lie": "lay", "lead": "led", "read": "read",
            "grow": "grew", "lose": "lost", "fall": "fell", "send": "sent",
            "build": "built", "understand": "understood", "draw": "drew",
            "break": "broke", "spend": "spent", "cut": "cut", "rise": "rose",
            "drive": "drove", "buy": "bought", "wear": "wore", "choose": "chose",
            "propose": "proposed","bear": "was born",
        }

    def _get_learned_templates(self) -> List[str]:
        """Fetch high-frequency grammar patterns from DB."""
        if not self.mm: return []
        try:
            with self.mm.ltm as conn:
                # Get top 15 most common patterns
                rows = conn._get_connection().execute(
                    "SELECT template FROM grammar_patterns WHERE frequency > 1 ORDER BY frequency DESC LIMIT 15"
                ).fetchall()
                return [r['template'] for r in rows]
        except:
            return []

    def realize_thought(self, thought: Dict[str, Any]) -> str:
        t_type = thought.get("type")
        subject = thought.get("subject", "It")
        facts = thought.get("facts", [])
        subject = self._clean_text(subject)

        if t_type == "definition":
            return self._realize_narrative(subject, facts)
        elif t_type == "error":
            return f"I lack data on '{subject}'."
        else:
            return "Thinking process complete."

    def _realize_narrative(self, subject: str, facts: List[tuple]) -> str:
        sentences = []
        
        # A list of "High Value" verbs for a biography
        achievement_verbs = [
            "invent", "develop", "design", "create", "propose", "discover", 
            "build", "found", "establish", "write", "author", "produce",
            "demonstrate", "patent", "conceive"
        ]

        # --- 1. RELEVANCE SCORING ---
        def get_fact_score(fact):
            s, p, o = fact
            score = 0
            
            # Boost Achievements
            if any(v in p.lower() for v in achievement_verbs):
                score += 100

            # Definition Bonus
            if p in ["is", "was", "are", "were", "be", "mean", "means"]:
                if len(o) > 15: score += 40
                else: score -= 10 

            if len(o) > 30: score += 10
            
            # Penalties
            if o.lower() in ["it", "them", "him", "her", "this"]: score -= 50
            if len(o) < 5: score -= 20
            
            return score

        # Sort highest score first
        facts.sort(key=get_fact_score, reverse=True)
        # -----------------------------

        learned = self._get_learned_templates()
        pool = self.templates["definition"] + self.templates["fact"] + learned
        
        seen_concepts = set()

        for i, (s, p, o) in enumerate(facts):
            # Skip duplicates or low quality
            if i > 2 and get_fact_score((s,p,o)) < 0: continue
            
            key = f"{p} {o[:10]}"
            if key in seen_concepts: continue
            seen_concepts.add(key)

            s = self._clean_text(s)
            o = self._clean_text(o)
            
            # --- 2. SMARTER CONJUGATION (The Fix) ---
            # Handle "write In", "go To" by conjugating only the first word
            p_words = p.split()
            first_word = p_words[0]
            
            if first_word in self.irregular_verbs:
                p_words[0] = self.irregular_verbs[first_word]
                p = " ".join(p_words)
            elif not first_word.endswith(("ed", "s", "ing")):
                # Regular verb conjugation
                if first_word.endswith("e"): p_words[0] += "d"
                else: p_words[0] += "ed"
                p = " ".join(p_words)
            # ----------------------------------------

            # 3. TEMPLATE SELECTION
            valid_templates = [t for t in pool if "{subject}" in t and "{object}" in t]
            
            current_score = get_fact_score((s, p, o))
            
            if current_score >= 100:
                # Achievements get simple templates to shine
                tmpl = "{subject} {predicate} {object}."
                sent = tmpl.format(subject=s, predicate=p, object=o)
            elif current_score >= 40:
                # Definitions
                def_templates = [t for t in self.templates["definition"] if "{predicate}" in t or p.split()[0] in ["is", "was"]]
                if def_templates:
                    sent = random.choice(def_templates).format(subject=s, predicate=p, object=o)
                else:
                    sent = f"{s} {p} {o}."
            else:
                sent = f"{s} {p} {o}."

            # Capitalize
            sent = sent[0].upper() + sent[1:]
            sentences.append(sent)
            
            if i >= 4: break 

        return " ".join(sentences)

    def generate_unknown(self, target: str) -> str:
        return random.choice(self.templates["unknown"]).format(target=target)

    def generate_definition(self, subject: str, definition: str) -> str:
        return self._realize_narrative(subject, [(subject, "is", definition)])

    def _clean_text(self, text: str) -> str:
        if not text: return ""
        
        # 1. Remove bracketed citations [12], [note 1]
        text = re.sub(r'\[.*?\]', '', text)
        
        # 2. Remove trailing citation numbers (e.g. "children.15" -> "children.")
        # Looks for a dot followed immediately by digits at the end of a word
        text = re.sub(r'\.(\d+)', '.', text)
        
        # 3. Remove stray brackets
        text = text.replace("]", "").replace("[", "")
        
        # 4. Remove artifacts
        text = text.replace("Output:", "")
        
        # 5. Squash Whitespace (The "Colorado Springs" Fix)
        # Replaces any sequence of whitespace (tabs, newlines, spaces) with a single space
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()