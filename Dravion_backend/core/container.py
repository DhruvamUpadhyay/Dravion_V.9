from typing import Any, Dict, Type
from core.logger import log

class DIContainer:
    """
    Lightweight Dependency Injection Container
    """
    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._named_services: Dict[str, Any] = {}

    def register(self, service_type: Type, instance: Any):
        self._services[service_type] = instance
        log.debug("service_registered", type=service_type.__name__)

    def register_named(self, name: str, instance: Any):
        self._named_services[name] = instance
        log.debug("named_service_registered", name=name)

    def resolve(self, service_type: Type) -> Any:
        if service_type not in self._services:
            log.error("service_not_found", type=service_type.__name__)
            raise KeyError(f"Service of type {service_type.__name__} not registered")
        return self._services[service_type]

    def resolve_named(self, name: str) -> Any:
        if name not in self._named_services:
            log.error("named_service_not_found", name=name)
            raise KeyError(f"Named service '{name}' not registered")
        return self._named_services[name]

# Global DI container
container = DIContainer()
