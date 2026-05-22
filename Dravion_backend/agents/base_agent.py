from abc import ABC, abstractmethod
from typing import Any, Dict
from dataclasses import dataclass
from tasks.task import Task
from core.logger import log


@dataclass
class AgentResult:
    status: str
    data: Dict[str, Any]
    error: str = None

    @classmethod
    def success(cls, data: Dict[str, Any]) -> "AgentResult":
        return cls(status="success", data=data)

    @classmethod
    def fallback(cls, error_msg: str) -> "AgentResult":
        return cls(status="fallback", data={"message": error_msg}, error=error_msg)


class BaseAgent(ABC):
    """Abstract base — all agents inherit this, with circuit breaker logic."""

    def __init__(self, name: str):
        self.name = name
        self.failure_count: int = 0
        self.failure_threshold: int = 3
        self.circuit_open: bool = False

    async def run(self, task: Task) -> AgentResult:
        if self.circuit_open:
            return AgentResult.fallback(f"{self.name} is temporarily unavailable.")

        try:
            result = await self._execute(task)
            self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            log.error("agent_failure", agent=self.name, error=str(e), count=self.failure_count)
            if self.failure_count >= self.failure_threshold:
                self.circuit_open = True
                log.critical("circuit_open", agent=self.name)
            raise e

    @abstractmethod
    async def _execute(self, task: Task) -> AgentResult:
        pass
