from tasks.task import Task
from agents.conversation_agent import ConversationAgent
from agents.search_agent import SearchAgent
from core.logger import log

class Router:
    """
    Routes tasks to correct agent
    """
    def __init__(self):
        # Sub-agents deactivated for now. Only core conversation is active.
        self.agents = {
            "conversation_agent": ConversationAgent()
            # "search_agent": SearchAgent() # Dormant (like EDITH/FRIDAY)
            # "adverse_agent": AdverseAgent() # Dormant
        }

    async def route(self, task: Task) -> Any:
        agent_name = task.agent
        agent = self.agents.get(agent_name)
        
        if not agent:
            log.error("no_agent_found", agent=agent_name)
            raise ValueError(f"Agent {agent_name} not found")
            
        log.debug("routing_task_to_agent", task_id=task.id, agent=agent_name)
        return await agent.run(task)

router = Router()
