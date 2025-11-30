# sns2f_framework/core/grammar_learner.py

import spacy
import logging
import hashlib
from typing import List, Tuple

log = logging.getLogger(__name__)

class GrammarLearner:
    """
    Phase 3: Grammar Induction Engine.
    Reads text and extracts reusable sentence templates.
    """

    def __init__(self, memory_manager):
        self.mm = memory_manager
        log.info("Loading Spacy for Grammar Learning...")
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            self.nlp = None

    def learn(self, text: str):
        """
        Ingests text, extracts patterns, and saves them to the DB.
        """
        if not self.nlp: return

        doc = self.nlp(text)
        
        for sent in doc.sents:
            # FIX: Relaxed constraints (3 to 35 words) to catch more Wikipedia sentences
            if len(sent) < 3 or len(sent) > 35:
                continue
                
            self._process_sentence(sent)

    def _process_sentence(self, sent):
        """
        Converts a specific sentence into an abstract template.
        """
        tokens = []
        pos_tags = []
        
        has_subject = False
        
        for token in sent:
            # abstract Noun Phrases
            if token.dep_ in ("nsubj", "nsubjpass"):
                tokens.append("{subject}")
                pos_tags.append("SUBJECT")
                has_subject = True
            elif token.dep_ in ("dobj", "attr", "pobj"):
                # We keep the object abstraction but don't strictly require it 
                # if the sentence structure is interesting otherwise
                tokens.append("{object}")
                pos_tags.append("OBJECT")
            # Keep common function words
            elif token.is_stop or token.pos_ in ("AUX", "ADP", "DET", "CCONJ"):
                tokens.append(token.text.lower())
                pos_tags.append(token.text.lower())
            # Abstract Content words
            elif token.pos_ == "ADJ":
                tokens.append("{adjective}")
                pos_tags.append("ADJ")
            elif token.pos_ == "VERB":
                tokens.append(token.lemma_) 
                pos_tags.append("VERB")
            # Punctuation
            elif token.is_punct:
                tokens.append(token.text)
                pos_tags.append("PUNCT")
            else:
                tokens.append(token.text)
                pos_tags.append(token.pos_)

        # FIX: Only require Subject. Many good sentences don't have a direct object.
        if has_subject:
            template = " ".join(tokens)
            pos_sequence = " ".join(pos_tags)
            
            # Sanity check: Ensure template has valid placeholders
            if "{subject}" in template and ("{object}" in template or "{adjective}" in template):
                self._save_pattern(template, pos_sequence, sent.text)

    def _save_pattern(self, template: str, pos_seq: str, example: str):
        """
        Persists the pattern to SQLite using an UPSERT strategy.
        """
        # Cleanup template spacing (fix " . " to ".")
        template = template.replace(" .", ".").replace(" ,", ",")
        
        p_hash = hashlib.md5(pos_seq.encode()).hexdigest()
        
        with self.mm.ltm as conn:
            cursor = conn._get_connection().execute(
                "SELECT id, frequency FROM grammar_patterns WHERE structure_hash = ?", 
                (p_hash,)
            )
            row = cursor.fetchone()
            
            if row:
                new_freq = row['frequency'] + 1
                conn._get_connection().execute(
                    "UPDATE grammar_patterns SET frequency = ? WHERE id = ?",
                    (new_freq, row['id'])
                )
                # FIX: Make this log visible for every hit to prove it's working
                log.info(f"Grammar Reinforcement: '{template}' (Seen {new_freq} times)")
            else:
                conn._get_connection().execute(
                    "INSERT INTO grammar_patterns (structure_hash, template, pos_sequence, example_sentence) VALUES (?, ?, ?, ?)",
                    (p_hash, template, pos_seq, example)
                )
                log.info(f"Learned New Pattern: {template}")