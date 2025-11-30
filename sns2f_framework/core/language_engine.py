# sns2f_framework/core/language_engine.py

import spacy
import logging
import re
from typing import Dict, Any, List

log = logging.getLogger(__name__)

class LanguageEngine:
    """
    The Non-LLM Linguistic Processor.
    V5.1: Fixed Regex Parsing.
    """
    
    def __init__(self):
        log.info("Loading Spacy (en_core_web_sm)...")
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            log.critical("Spacy model not found. Run: python -m spacy download en_core_web_sm")
            self.nlp = None

    def parse_query(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower().strip()
        
        # --- LEVEL 1: REGEX PATTERNS ---
        
        # 1. Time/Date Pattern: "When..."
        if text_lower.startswith("when"):
            target = text
            # FIX: Removed "?" from this list to prevent Regex crash
            stopwords = ["when", "did", "was", "is", "born", "die", "happen", "occur", "the"]
            for word in stopwords:
                # Case-insensitive replace of whole words
                target = re.sub(f"\\b{word}\\b", "", target, flags=re.IGNORECASE)
            
            # Handle punctuation manually
            target = target.replace("?", "").strip()
            
            return {
                "intent": "query:time",
                "target": target
            }

        # 2. Math Pattern
        if re.search(r'\d+\s*[\+\-\*\/]\s*\d+', text) or text_lower.startswith(("calculate", "solve")):
            return {
                "intent": "action:calculate",
                "expression": text,
                "target": text
            }

        # 3. Definition Pattern
        match = re.match(r'^(who|what)\s+is\s+(.+?)(\?)?$', text_lower)
        if match:
            target = match.group(2).strip()
            return {
                "intent": "query:definition",
                "target": target.title()
            }
            
        # 4. Explanation Pattern
        if text_lower.startswith(("explain", "describe", "tell me about")):
            target = re.sub(r'^(explain|describe|tell me about)\s+', "", text_lower, flags=re.IGNORECASE)
            return {
                "intent": "query:definition", 
                "target": target.strip("?. ").title()
            }

        # --- LEVEL 2: SPACY FALLBACK ---
        
        if not self.nlp: 
            return {"intent": "unknown", "target": text}
        
        doc = self.nlp(text)
        
        potential_targets = [chunk.text for chunk in doc.noun_chunks]
        target = potential_targets[-1] if potential_targets else text

        return {
            "intent": "query:definition", 
            "target": target.strip("?. ")
        }

    def extract_triples_rule_based(self, text: str) -> List[tuple]:
        if not self.nlp: return []
        doc = self.nlp(text)
        triples = []
        
        bad_words = {"he", "she", "it", "they", "we", "i", "you", "this", "that", "who", "what", "which", "there"}
        
        for sent in doc.sents:
            subj, verb, obj = None, None, None
            
            for token in sent:
                if token.pos_ in ["VERB", "AUX"]:
                    verb = token.lemma_
                    
                    for child in token.children:
                        if child.dep_ in ("nsubj", "nsubjpass"):
                            subj = " ".join([t.text for t in child.subtree])
                    
                    for child in token.children:
                        if child.dep_ in ("dobj", "attr", "acomp"):
                            obj = " ".join([t.text for t in child.subtree])
                        elif child.dep_ == "prep":
                            if not obj:
                                verb_phrase = f"{verb} {child.text}"
                                pobjs = [p for p in child.children if p.dep_ == "pobj"]
                                if pobjs:
                                    verb = verb_phrase
                                    obj = " ".join([t.text for t in pobjs[0].subtree])

            if subj and verb and obj:
                subj = subj.replace("\n", " ").strip()
                obj = obj.replace("\n", " ").strip(" .")
                
                if len(subj) < 2 or len(obj) < 2: continue
                if subj.lower().split()[0] in bad_words: continue
                
                if subj.lower().startswith(("a ", "an ", "the ")): 
                    subj = subj.split(" ", 1)[1]
                
                triples.append((subj, verb, obj))
                
        return triples