from abc import ABC, abstractmethod

class BaseSkill(ABC):
    """
    Abstract template for all Turiya Skills.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the skill (e.g., 'calculator')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """What this skill does."""
        pass

    @property
    @abstractmethod
    def triggers(self) -> list:
        """List of keywords or regex patterns that activate this skill."""
        pass

    @abstractmethod
    def execute(self, input_text: str) -> str:
        """The logic. Returns the result as a string."""
        pass