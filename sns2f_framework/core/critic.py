# sns2f_framework/core/critic.py

import logging
import re

log = logging.getLogger(__name__)

class Critic:
    """
    The Quality Assurance Engine.
    Reviews generated text for artifacts, repetition, and broken logic.
    """

    def evaluate(self, text: str) -> str:
        """
        Input: Raw generated text.
        Output: Cleaned text + Warning label (if quality is low).
        """
        score = 100
        issues = []

        # 1. Check for Template Artifacts (The "Curly Brace" Bug)
        # If we see {subject} or {object} left over, the template failed.
        if re.search(r'\{.*?\}', text):
            score -= 50
            issues.append("Broken Template")
            # Emergency cleanup: remove the braces
            text = re.sub(r'\{.*?\}', 'something', text)

        # 2. Check for Scraping Artifacts (The "Wiki" Bug)
        # e.g. "computers.[32]" or "Turing]"
        if re.search(r'\[\d+\]|\]', text):
            score -= 10
            issues.append("Citation Artifacts")
            text = re.sub(r'\[.*?\]|\]', '', text)

        # 3. Check for Repetition (The "Stuttering" Bug)
        # Symbolic systems often repeat the same fact if it appears twice in DB
        sentences = text.split('.')
        unique_sentences = []
        seen = set()
        for s in sentences:
            clean_s = s.strip().lower()
            if clean_s and clean_s not in seen:
                seen.add(clean_s)
                unique_sentences.append(s.strip())
            elif clean_s:
                score -= 20
                issues.append("Repetition")
        
        # Reconstruct without duplicates
        cleaned_text = ". ".join(unique_sentences)
        if unique_sentences: cleaned_text += "."

        # 4. Grading
        if score < 50:
            log.warning(f"Critic rejected output. Issues: {issues}")
            return "I have data, but I cannot phrase it clearly right now."
        
        if score < 90:
            log.info(f"Critic flagged minor issues: {issues}")
            # We return the cleaned text
            return cleaned_text

        return cleaned_text