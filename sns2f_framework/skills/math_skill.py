from sns2f_framework.skills.base_skill import BaseSkill
from sns2f_framework.tools.code_executor import CodeExecutor
import re

class MathSkill(BaseSkill):
    @property
    def name(self):
        return "Math & Logic Interpreter"

    @property
    def description(self):
        return "Solves math problems by writing and executing Python code."

    @property
    def triggers(self):
        return ["calculate", "solve", "compute", "+", "*", "/", "math"]

    def execute(self, input_text: str) -> str:
        # FIX: Use Regex for case-insensitive removal of keywords
        # Remove "calculate", "solve", "compute", "what is"
        clean_expr = re.sub(r'(?i)\b(calculate|solve|compute|what is)\b', '', input_text)
        
        # Cleanup whitespace and question marks
        clean_expr = clean_expr.strip("?. ")
        
        try:
            # Wrap in print
            code = f"print({clean_expr})"
            result = CodeExecutor.execute(code)
            return f"🧮 Calculated Result: {result}"
        except Exception as e:
            return f"Math Error: {e} (Tried running: '{clean_expr}')"