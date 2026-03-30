"""
SkillRegistry — centralised catalogue of all available MCP Skills.

Usage:
    # Auto-register via decorator (preferred):
    @register_skill
    class MySkill(MCPSkill):
        ...

    # Manual registration:
    registry = SkillRegistry()
    registry.register(MySkill())

    # Retrieval:
    skill = registry.get("my_skill_name")
    all_names = registry.list_all()
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from .skill_base import MCPSkill


class SkillRegistry:
    """
    Singleton catalogue of instantiated MCPSkill objects.

    Thread-safe for reads (dict lookup is atomic in CPython).
    Registration should occur at import time via @register_skill.
    """

    _instance: "SkillRegistry | None" = None
    _skills: dict[str, "MCPSkill"]

    def __new__(cls) -> "SkillRegistry":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._skills = {}
            cls._instance = instance
        return cls._instance

    # ── Registration ─────────────────────────────────────────────────────────

    def register(self, skill: "MCPSkill") -> None:
        """
        Add a Skill instance to the registry.

        Overwrites any existing registration with the same name,
        allowing hot-reload in development.
        """
        self._skills[skill.name] = skill

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def get(self, name: str) -> "MCPSkill":
        """
        Retrieve a registered Skill by its name.

        Raises:
            KeyError: if name is not registered.
        """
        if name not in self._skills:
            available = ", ".join(sorted(self._skills)) or "(none)"
            raise KeyError(
                f"Skill '{name}' not found in registry. "
                f"Available: {available}"
            )
        return self._skills[name]

    def list_all(self) -> list[str]:
        """Return sorted list of all registered Skill names."""
        return sorted(self._skills.keys())

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, name: str) -> bool:
        return name in self._skills

    def __repr__(self) -> str:
        return f"SkillRegistry({len(self._skills)} skills registered)"


# ── Module-level singleton ────────────────────────────────────────────────────

_registry = SkillRegistry()


def register_skill(cls: Type["MCPSkill"]) -> Type["MCPSkill"]:
    """
    Class decorator that auto-registers a Skill in the global registry.

    The class is instantiated once at decoration time and stored.
    Use this to register Skills at import time.

    Example:
        @register_skill
        class APIFootballFixturesExtractor(APIFootballBaseSkill):
            ...
    """
    _registry.register(cls())
    return cls
