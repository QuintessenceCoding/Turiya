import pkgutil
import importlib
import inspect
import logging
import sns2f_framework.skills as skills_package
from sns2f_framework.skills.base_skill import BaseSkill

log = logging.getLogger(__name__)

class SkillRegistry:
    """
    The Tool Manager.
    Dynamically loads skills from the 'skills' folder and matches them to user queries.
    """
    
    def __init__(self):
        self.skills = []
        self._load_skills()

    def _load_skills(self):
        """Reflection magic to find all skill classes."""
        log.info("Loading Skills...")
        path = skills_package.__path__
        prefix = skills_package.__name__ + "."

        for _, name, _ in pkgutil.iter_modules(path, prefix):
            module = importlib.import_module(name)
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BaseSkill) and obj is not BaseSkill:
                    skill_instance = obj()
                    self.skills.append(skill_instance)
                    log.info(f"Skill Loaded: {skill_instance.name}")

    def match_skill(self, text: str, intent: str):
        """
        Decides if a skill should handle this query.
        Prioritizes Intent first, then Keyword Matching.
        """
        text_lower = text.lower()

        # 1. Intent Match (From LanguageEngine)
        if intent == "action:calculate":
            for skill in self.skills:
                if "Math" in skill.name: return skill

        # 2. Keyword Match
        for skill in self.skills:
            for trigger in skill.triggers:
                if trigger in text_lower:
                    return skill
        
        return None