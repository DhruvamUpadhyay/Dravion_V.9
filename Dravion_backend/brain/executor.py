from tasks.task import Task
from core.logger import log

class Executor:
    """
    Executes agent responses and formats output
    """
    def __init__(self):
        pass

    async def process_result(self, result: dict) -> str:
        """
        Extracts speech text or UI data from the agent's result dict
        """
        if result.get("status") == "fallback":
            return result.get("data", {}).get("message", "I encountered an error.")
            
        return result.get("data", {}).get("response", "Done.")

executor = Executor()
