"""
DRAVION v.9 — Memory Manager

Unified interface across all memory tiers:
  Tier 1: Working (in-memory dict, will be Redis later)
  Tier 2: Episodic (SQLite conversation logs)
  Tier 3: Semantic (ChromaDB vector search)
  Tier 4: Adaptive (learned preferences, behaviors, facts)
"""
from typing import Dict, Any, List
from memory.working import working_memory
from memory.episodic import EpisodicMemory
from memory.semantic import SemanticMemory
from memory.adaptive import adaptive_memory
from core.logger import log


class MemoryManager:
    def __init__(self):
        self.working = working_memory
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.adaptive = adaptive_memory
        log.info("memory_manager_ready")

    def get_conversation_history(self, n: int = 6) -> List[Dict[str, str]]:
        return self.episodic.get_recent(n)

    def search_knowledge(self, query: str) -> list:
        return self.semantic.search(query)

    def remember_conversation(self, user_input: str, agent_output: str):
        self.episodic.add_interaction(user_input, agent_output)

    def remember_fact(self, fact: str, source: str = "conversation"):
        self.semantic.store(fact, metadata={"source": source})

    def get_adaptive_context(self) -> str:
        """Get personality/preference context for system prompt injection."""
        return self.adaptive.get_context_injection()

    async def learn_from_conversation(self, user_msg: str, agent_msg: str):
        """Background: extract learnable facts from this turn."""
        await self.adaptive.extract_from_conversation(user_msg, agent_msg)
