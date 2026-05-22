import asyncio
from typing import Callable, Any, Dict, List, Set
from core.logger import log

class EventBus:
    """
    Central pub/sub message bus (asyncio-based)
    """
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        # Predefined topics as per v2 spec
        self.topics: Set[str] = {
            "user.input",          # Raw user input (voice or text)
            "intent.detected",     # Planner output
            "task.created",        # New task in registry
            "task.completed",      # Task done
            "agent.response",      # Agent output ready
            "memory.store",        # Memory write request
            "skill.triggered",     # A skill was matched
            "error.occurred",      # Any module error
            "system.shutdown",     # Graceful shutdown signal
        }

    def subscribe(self, topic: str, callback: Callable):
        if topic not in self.topics:
            log.warning("subscribing_to_unknown_topic", topic=topic)
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)
        log.debug("subscribed", topic=topic, callback=callback.__name__)

    async def publish(self, topic: str, data: Any):
        if topic not in self.topics:
            log.warning("publishing_to_unknown_topic", topic=topic)
        
        if topic in self.subscribers:
            log.debug("publishing_event", topic=topic, subscribers=len(self.subscribers[topic]))
            # Run all callbacks concurrently
            tasks = [asyncio.create_task(self._safe_execute(cb, data, topic)) for cb in self.subscribers[topic]]
            if tasks:
                await asyncio.gather(*tasks)

    async def _safe_execute(self, callback: Callable, data: Any, topic: str):
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)
        except Exception as e:
            log.error("event_callback_failed", topic=topic, callback=callback.__name__, error=str(e))
            # Optional: push to error.occurred, but careful to avoid infinite loop
            # if topic != "error.occurred":
            #     await self.publish("error.occurred", {"source": "event_bus", "error": str(e)})

# Singleton instance
event_bus = EventBus()
