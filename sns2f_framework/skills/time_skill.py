from sns2f_framework.skills.base_skill import BaseSkill
from datetime import datetime

class TimeSkill(BaseSkill):
    @property
    def name(self):
        return "Chronometer"

    @property
    def description(self):
        return "Tells the current date and time."

    @property
    def triggers(self):
        return ["what time", "current time", "what date", "today's date", "what day"]

    def execute(self, input_text: str) -> str:
        now = datetime.now()
        return f"🕒 Current Date & Time: {now.strftime('%Y-%m-%d %H:%M:%S')}"