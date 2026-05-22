from typing import Dict, Type, Any, Callable
from core.logger import log

class SkillCollisionError(Exception):
    pass

class BaseSkill:
    """Base class for all skills"""
    name: str = "base_skill"
    version: str = "1.0"
    
    async def execute(self, **kwargs) -> Any:
        pass

class SkillsRegistry:
    """
    Skills registry with collision detection
    """
    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill):
        if skill.name in self._skills:
            raise SkillCollisionError(
                f"Skill '{skill.name}' already registered by "
                f"{self._skills[skill.name].__module__}"
            )
        self._skills[skill.name] = skill
        log.info("skill_registered", name=skill.name, version=skill.version)

    def get_skill(self, name: str) -> BaseSkill:
        return self._skills.get(name)

    def clear(self):
        self._skills.clear()

# Global registry
skills_registry = SkillsRegistry()
