from agents.base_agent import BaseAgent, AgentResult
from tasks.task import Task
from core.logger import log
from core.config import config
from google import genai
from google.genai import types

class SearchAgent(BaseAgent):
    """
    Handles web search, news, and current affairs using Gemini
    """
    def __init__(self):
        super().__init__(name="search_agent")
        # Initialize the new google.genai client
        if config.google_api_key and config.google_api_key != "your_google_api_key_here":
            self.client = genai.Client(api_key=config.google_api_key)
        else:
            self.client = None

    async def _execute(self, task: Task) -> AgentResult:
        if not self.client:
            return AgentResult.fallback("Gemini API key is missing or invalid.")
            
        log.info("processing_search", intent=task.intent)
        
        try:
            # We use gemini-2.5-pro or gemini-2.5-flash as per the latest API
            # Enabling Google Search grounding
            response = self.client.models.generate_content(
                model='gemini-2.5-pro',
                contents=task.intent,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
                    temperature=0.3
                )
            )
            
            return AgentResult.success({
                "response": response.text,
                "source": "gemini_search"
            })
        except Exception as e:
            log.error("gemini_search_failed", error=str(e))
            raise e
