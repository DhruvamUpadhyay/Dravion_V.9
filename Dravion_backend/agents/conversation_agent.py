from agents.base_agent import BaseAgent, AgentResult
from tasks.task import Task
from core.logger import log
from core.config import config
from memory.memory_manager import memory_manager
from openai import AsyncOpenAI
import asyncio

class ConversationAgent(BaseAgent):
    """
    General chat and Q&A handling agent.
    """
    def __init__(self):
        super().__init__(name="conversation_agent")
        self.client = AsyncOpenAI(
            base_url=config.ollama_base_url,
            api_key="ollama", # required but ignored
        )
        self.model = config.ollama_model

    async def _execute(self, task: Task) -> AgentResult:
        intent = task.intent
        log.info("processing_conversation", intent=intent)
        
        # Get context (recent episodic memory)
        context = memory_manager.get_context()
        
        system_prompt = "You are DRAVION, an advanced, highly capable AI assistant. Be concise, professional, and helpful. Do not use filler phrases."
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add recent conversation history if available
        if "episodic" in context and context["episodic"]:
            for turn in context["episodic"]:
                messages.append({"role": "user", "content": turn.get("user", "")})
                messages.append({"role": "assistant", "content": turn.get("agent", "")})
                
        # Add the current intent
        messages.append({"role": "user", "content": intent})
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7
            )
            
            response_text = response.choices[0].message.content
            
            # Store in memory for future turns
            memory_manager.store_interaction(user_input=intent, agent_output=response_text)
            
            return AgentResult.success({
                "response": response_text
            })
        except Exception as e:
            log.error("conversation_llm_failed", error=str(e))
            return AgentResult.fallback(f"I encountered a cognitive error: {str(e)}")
