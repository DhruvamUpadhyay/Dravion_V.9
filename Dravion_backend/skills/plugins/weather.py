from skills.registry import BaseSkill

class WeatherSkill(BaseSkill):
    name = "weather"
    version = "1.0"
    
    async def execute(self, city: str = "Mumbai", **kwargs):
        # Placeholder for real weather API
        return {
            "city": city,
            "temp": 32,
            "condition": "humid",
            "alert": None,
            "raw": f"{city}: 32°C, humid"
        }
