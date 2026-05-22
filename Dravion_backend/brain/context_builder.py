from memory.memory_manager import memory_manager
from core.logger import log

class ContextBuilder:
    """
    Assembles memory + history into LLM prompt
    """
    def __init__(self):
        pass

    def build_prompt(self, user_input: str) -> str:
        context = memory_manager.get_context(query=user_input)
        
        # Here we would format the context into a system prompt
        # For now, just return a string representation
        log.debug("context_built", working_size=len(context["working"]))
        
        return f"Context: {context}\nInput: {user_input}"

context_builder = ContextBuilder()
