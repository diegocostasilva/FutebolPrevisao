"""Tests for src/core/skill_registry.py"""

import pytest

from src.core.context import ExecutionContext
from src.core.result import SkillResult
from src.core.skill_base import MCPSkill
from src.core.skill_registry import SkillRegistry, register_skill


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_skill(skill_name: str, skill_version: str = "1.0.0") -> MCPSkill:
    """Factory to create a concrete MCPSkill with a given name."""

    class _Skill(MCPSkill):
        @property
        def name(self) -> str:
            return skill_name

        @property
        def version(self) -> str:
            return skill_version

        def validate(self, context: ExecutionContext) -> bool:
            return True

        def execute(self, context: ExecutionContext) -> SkillResult:
            return SkillResult.ok("ok")

    return _Skill()


@pytest.fixture(autouse=True)
def _clean_registry():
    """
    Isola o estado do registry para cada teste deste módulo.
    Salva o estado anterior e restaura ao final para não afetar outros módulos.
    """
    registry = SkillRegistry()
    saved = dict(registry._skills)
    registry._skills.clear()
    yield
    registry._skills.clear()
    registry._skills.update(saved)


# ── Singleton ─────────────────────────────────────────────────────────────────

class TestSkillRegistrySingleton:
    def test_same_instance(self):
        assert SkillRegistry() is SkillRegistry()

    def test_shared_state(self):
        r1 = SkillRegistry()
        r2 = SkillRegistry()
        r1.register(_make_skill("shared_skill"))
        assert "shared_skill" in r2


# ── Registration & retrieval ──────────────────────────────────────────────────

class TestSkillRegistryOperations:
    def test_register_and_get(self):
        registry = SkillRegistry()
        skill = _make_skill("test_skill")
        registry.register(skill)
        assert registry.get("test_skill") is skill

    def test_get_raises_key_error_for_unknown(self):
        with pytest.raises(KeyError, match="not found"):
            SkillRegistry().get("nonexistent_skill")

    def test_get_error_lists_available(self):
        registry = SkillRegistry()
        registry.register(_make_skill("alpha"))
        with pytest.raises(KeyError, match="alpha"):
            registry.get("beta")

    def test_register_overwrites_existing(self):
        registry = SkillRegistry()
        old = _make_skill("my_skill", "1.0.0")
        new = _make_skill("my_skill", "2.0.0")
        registry.register(old)
        registry.register(new)
        assert registry.get("my_skill").version == "2.0.0"

    def test_list_all_returns_sorted(self):
        registry = SkillRegistry()
        for name in ["zebra", "alpha", "mango"]:
            registry.register(_make_skill(name))
        assert registry.list_all() == ["alpha", "mango", "zebra"]

    def test_list_all_empty(self):
        assert SkillRegistry().list_all() == []

    def test_len(self):
        registry = SkillRegistry()
        registry.register(_make_skill("a"))
        registry.register(_make_skill("b"))
        assert len(registry) == 2

    def test_contains(self):
        registry = SkillRegistry()
        registry.register(_make_skill("present"))
        assert "present" in registry
        assert "absent" not in registry


# ── Decorator ─────────────────────────────────────────────────────────────────

class TestRegisterSkillDecorator:
    def test_decorator_registers_skill(self):
        @register_skill
        class _DecoratedSkill(MCPSkill):
            @property
            def name(self) -> str:
                return "decorated_skill"

            @property
            def version(self) -> str:
                return "1.0.0"

            def validate(self, context: ExecutionContext) -> bool:
                return True

            def execute(self, context: ExecutionContext) -> SkillResult:
                return SkillResult.ok("ok")

        assert "decorated_skill" in SkillRegistry()

    def test_decorator_returns_original_class(self):
        @register_skill
        class _ReturnedSkill(MCPSkill):
            @property
            def name(self) -> str:
                return "returned_skill"

            @property
            def version(self) -> str:
                return "1.0.0"

            def validate(self, context: ExecutionContext) -> bool:
                return True

            def execute(self, context: ExecutionContext) -> SkillResult:
                return SkillResult.ok("ok")

        # Decorator must return the class so it can still be instantiated
        assert issubclass(_ReturnedSkill, MCPSkill)
