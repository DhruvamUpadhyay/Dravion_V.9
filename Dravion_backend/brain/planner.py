import json
from typing import List
from tasks.task import Task
from core.config import config
from core.logger import log
from openai import AsyncOpenAI
from memory.memory_manager import memory_manager

class Planner:
    """
    Breaks user intent into sub-tasks (ReAct loop step 1) using local Gemma 4
    """
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=config.ollama_base_url,
            api_key="ollama", # required but ignored
        )
        self.model = config.ollama_model

    async def create_plan(self, user_input: str) -> List[Task]:
        """
        Takes raw user input and turns it into a list of Tasks
        """
        log.debug("planning_tasks_for", input=user_input)
        
        context = memory_manager.get_context(query=user_input)
        
        system_prompt = """You are DRAVION, an advanced autonomous system.
Your job is to analyze the user's input and break it into a task.
Return ONLY valid JSON in the following format:
{
  "intent": "clean intent summary",
  "agent": "conversation_agent" | "search_agent" | "adverse_agent",
  "priority": 5
}
Use 'search_agent' for news, weather, or web searches.
Use 'adverse_agent' for OSINT or security tasks.
Use 'conversation_agent' for general chat, coding, or instructions.
"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context: {context}\n\nUser Input: {user_input}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            result_text = response.choices[0].message.content
            plan_data = json.loads(result_text)
            
            task = Task(
                intent=plan_data.get("intent", user_input),
                agent=plan_data.get("agent", "conversation_agent"),
                priority=plan_data.get("priority", 5)
            )
            return [task]
            
        except Exception as e:
            log.error("planner_llm_failed", error=str(e))
            # Fallback to general conversation if LLM fails
            return [Task(intent=user_input, agent="conversation_agent")]

planner = Planner()
