"""Tests for src/core/skill_base.py"""

import pytest

from src.core.context import ExecutionContext
from src.core.exceptions import MCPValidationError
from src.core.result import SkillResult
from src.core.skill_base import MCPSkill


class _DummySkill(MCPSkill):
    """Minimal concrete implementation for testing MCPSkill contract."""

    @property
    def name(self) -> str:
        return "dummy_skill"

    @property
    def version(self) -> str:
        return "1.0.0"

    def validate(self, context: ExecutionContext) -> bool:
        if not context.api_football_key:
            raise MCPValidationError("missing api key", skill_name=self.name)
        return True

    def execute(self, context: ExecutionContext) -> SkillResult:
        return SkillResult.ok("done", rows_affected=1)


class _RollbackSkill(_DummySkill):
    """Skill that tracks rollback calls."""

    rolled_back = False

    def rollback(self, context: ExecutionContext) -> None:
        _RollbackSkill.rolled_back = True


class TestMCPSkillContract:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            MCPSkill()  # type: ignore[abstract]

    def test_name_property(self):
        assert _DummySkill().name == "dummy_skill"

    def test_version_property(self):
        assert _DummySkill().version == "1.0.0"

    def test_validate_returns_true_on_valid_context(self, mock_context):
        assert _DummySkill().validate(mock_context) is True

    def test_validate_raises_on_missing_key(self, empty_context):
        with pytest.raises(MCPValidationError):
            _DummySkill().validate(empty_context)

    def test_execute_returns_skill_result(self, mock_context):
        result = _DummySkill().execute(mock_context)
        assert isinstance(result, SkillResult)
        assert result.success is True

    def test_rollback_default_is_noop(self, mock_context):
        """Default rollback must not raise."""
        _DummySkill().rollback(mock_context)  # no exception expected

    def test_rollback_override_is_called(self, mock_context):
        skill = _RollbackSkill()
        _RollbackSkill.rolled_back = False
        skill.rollback(mock_context)
        assert _RollbackSkill.rolled_back is True


class TestMCPSkillStr:
    def test_str_format(self):
        assert str(_DummySkill()) == "dummy_skill v1.0.0"

    def test_repr_format(self):
        r = repr(_DummySkill())
        assert "DummySkill" in r
        assert "dummy_skill" in r
        assert "1.0.0" in r
