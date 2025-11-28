# sns2f_framework/reasoning/symbolic_engine.py

import logging
from typing import List, Tuple, Any

log = logging.getLogger(__name__)

class SymbolicEngine:
    """
    A helper engine that prompts an LLM to extract structured
    Subject-Predicate-Object triples from raw text.
    """

    @staticmethod
    def extract_triples(text: str, llm_callable: Any) -> List[Tuple[str, str, str]]:
        # Simplified "Few-Shot" prompt for smaller models
        prompt = (
            f"Extract logic triples (Subject | Predicate | Object) from the text.\n\n"
            f"Text: Ants use pheromones to communicate.\n"
            f"Output: Ants | use | pheromones\n"
            f"Output: Ants | communicate via | pheromones\n\n"
            f"Text: The SNS framework runs on CPU.\n"
            f"Output: SNS framework | runs on | CPU\n\n"
            f"Text: {text}\n"
            f"Output:"
        )
        
        try:
            output = llm_callable(
                prompt,
                max_tokens=100,
                stop=["\n\n", "Text:"], # Stop before generating a new fake example
                echo=False,
                temperature=0.1
            )
            
            raw_response = output['choices'][0]['text'].strip()
            
            # --- DEBUG ---
            log.debug(f"raw_logic_output: {raw_response}") 
            # -------------
            
            triples = []
            for line in raw_response.split('\n'):
                # --- FIX: CLEANUP ---
                # Remove artifacts like "Output:" or numbering "1."
                line = line.replace("Output:", "").replace("Output", "").strip()
                # --------------------
                
                if "|" in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) == 3:
                        s, p, o = parts
                        if len(s) < 50 and len(o) < 50:
                            triples.append((s, p, o))
            
            return triples
            
        except Exception as e:
            log.error(f"Symbolic extraction failed: {e}")
            return []