"""DRAVION v.9 — Task Model"""
import uuid
from enum import Enum
from dataclasses import dataclass, field


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    intent: str
    agent: str = "conversation_agent"
    priority: int = 5
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: TaskStatus = TaskStatus.PENDING
