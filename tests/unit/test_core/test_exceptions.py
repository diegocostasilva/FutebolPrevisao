"""Tests for src/core/exceptions.py"""

import pytest

from src.core.exceptions import (
    MCPDataLeakageError,
    MCPExecutionError,
    MCPQuotaExceededError,
    MCPSkillError,
    MCPValidationError,
)


class TestMCPSkillError:
    def test_is_exception(self):
        assert issubclass(MCPSkillError, Exception)

    def test_message(self):
        err = MCPSkillError("something went wrong")
        assert str(err) == "something went wrong"

    def test_with_skill_name_and_version(self):
        err = MCPSkillError("oops", skill_name="my_skill", skill_version="1.0.0")
        assert "[my_skill v1.0.0]" in str(err)
        assert err.skill_name == "my_skill"
        assert err.skill_version == "1.0.0"

    def test_without_skill_name(self):
        err = MCPSkillError("bare error")
        assert str(err) == "bare error"


class TestHierarchy:
    def test_validation_is_skill_error(self):
        assert issubclass(MCPValidationError, MCPSkillError)

    def test_execution_is_skill_error(self):
        assert issubclass(MCPExecutionError, MCPSkillError)

    def test_quota_is_skill_error(self):
        assert issubclass(MCPQuotaExceededError, MCPSkillError)

    def test_leakage_is_skill_error(self):
        assert issubclass(MCPDataLeakageError, MCPSkillError)

    def test_catch_base_catches_child(self):
        with pytest.raises(MCPSkillError):
            raise MCPValidationError("missing api key")


class TestMCPQuotaExceededError:
    def test_stores_quota_info(self):
        err = MCPQuotaExceededError("quota gone", remaining=0, limit=100)
        assert err.remaining == 0
        assert err.limit == 100

    def test_raise_and_catch(self):
        with pytest.raises(MCPQuotaExceededError) as exc_info:
            raise MCPQuotaExceededError("out of quota", remaining=0, limit=7500)
        assert exc_info.value.limit == 7500


class TestMCPDataLeakageError:
    def test_stores_feature_and_fixture(self):
        err = MCPDataLeakageError(
            "future data detected",
            feature_name="goals_home",
            fixture_id=12345,
        )
        assert err.feature_name == "goals_home"
        assert err.fixture_id == 12345
