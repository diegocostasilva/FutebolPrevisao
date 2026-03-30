"""Testes para src/agents/base_agent.py"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.base_agent import BaseAgent
from src.core.context import ExecutionContext
from src.core.exceptions import MCPValidationError
from src.core.result import SkillResult
from src.core.skill_base import MCPSkill


# ── Skills auxiliares ─────────────────────────────────────────────────────────

def _ok_skill(name: str = "ok_skill") -> MCPSkill:
    skill = MagicMock(spec=MCPSkill)
    skill.name = name
    skill.version = "1.0.0"
    skill.validate.return_value = True
    skill.execute.return_value = SkillResult.ok("done", rows_affected=5)
    skill.rollback = MagicMock()
    return skill


def _fail_skill(name: str = "fail_skill") -> MCPSkill:
    skill = MagicMock(spec=MCPSkill)
    skill.name = name
    skill.version = "1.0.0"
    skill.validate.return_value = True
    skill.execute.return_value = SkillResult.fail("algo deu errado")
    skill.rollback = MagicMock()
    return skill


def _error_skill(name: str = "error_skill") -> MCPSkill:
    skill = MagicMock(spec=MCPSkill)
    skill.name = name
    skill.version = "1.0.0"
    skill.validate.return_value = True
    skill.execute.side_effect = RuntimeError("explosão")
    skill.rollback = MagicMock()
    return skill


def _validation_error_skill(name: str = "validation_fail_skill") -> MCPSkill:
    skill = MagicMock(spec=MCPSkill)
    skill.name = name
    skill.version = "1.0.0"
    skill.validate.side_effect = MCPValidationError("validação falhou")
    skill.execute.return_value = SkillResult.ok("ok")
    skill.rollback = MagicMock()
    return skill


# ── Construção ────────────────────────────────────────────────────────────────

class TestBaseAgentConstruction:
    def test_stores_skills(self):
        skills = [_ok_skill("a"), _ok_skill("b")]
        agent = BaseAgent(skills)
        assert agent.skills == skills

    def test_default_max_retries(self):
        agent = BaseAgent([])
        assert agent.max_retries == 2

    def test_custom_max_retries(self):
        agent = BaseAgent([], max_retries=5)
        assert agent.max_retries == 5

    def test_agent_name_is_class_name(self):
        agent = BaseAgent([])
        assert agent.agent_name == "BaseAgent"


# ── Execução com sucesso ───────────────────────────────────────────────────────

class TestBaseAgentExecuteSuccess:
    def test_returns_list_of_results(self, mock_context):
        agent = BaseAgent([_ok_skill("a"), _ok_skill("b")])
        results = agent.execute(mock_context)
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_executes_in_order(self, mock_context):
        order = []
        s1, s2 = _ok_skill("first"), _ok_skill("second")
        s1.execute.side_effect = lambda ctx: (order.append("first"), SkillResult.ok("ok"))[1]
        s2.execute.side_effect = lambda ctx: (order.append("second"), SkillResult.ok("ok"))[1]

        BaseAgent([s1, s2]).execute(mock_context)
        assert order == ["first", "second"]

    def test_calls_validate_before_execute(self, mock_context):
        call_log = []
        skill = _ok_skill()
        skill.validate.side_effect = lambda ctx: call_log.append("validate") or True
        skill.execute.side_effect = lambda ctx: (call_log.append("execute"), SkillResult.ok("ok"))[1]

        BaseAgent([skill]).execute(mock_context)
        assert call_log == ["validate", "execute"]

    def test_empty_skill_list_returns_empty(self, mock_context):
        results = BaseAgent([]).execute(mock_context)
        assert results == []


# ── Fail-fast ─────────────────────────────────────────────────────────────────

class TestBaseAgentFailFast:
    @patch("src.agents.base_agent.time.sleep")
    def test_raises_on_skill_failure(self, mock_sleep, mock_context):
        agent = BaseAgent([_fail_skill()], max_retries=0)
        with pytest.raises(RuntimeError, match="fail_skill"):
            agent.execute(mock_context)

    @patch("src.agents.base_agent.time.sleep")
    def test_raises_on_skill_exception(self, mock_sleep, mock_context):
        agent = BaseAgent([_error_skill()], max_retries=0)
        with pytest.raises(RuntimeError, match="error_skill"):
            agent.execute(mock_context)

    @patch("src.agents.base_agent.time.sleep")
    def test_raises_on_validation_error(self, mock_sleep, mock_context):
        agent = BaseAgent([_validation_error_skill()], max_retries=0)
        with pytest.raises(RuntimeError):
            agent.execute(mock_context)

    @patch("src.agents.base_agent.time.sleep")
    def test_stops_at_first_failure(self, mock_sleep, mock_context):
        s2 = _ok_skill("second")
        agent = BaseAgent([_fail_skill(), s2], max_retries=0)

        with pytest.raises(RuntimeError):
            agent.execute(mock_context)

        s2.execute.assert_not_called()


# ── Rollback ──────────────────────────────────────────────────────────────────

class TestBaseAgentRollback:
    @patch("src.agents.base_agent.time.sleep")
    def test_rollback_called_on_failure(self, mock_sleep, mock_context):
        ok = _ok_skill("first")
        fail = _fail_skill("second")
        agent = BaseAgent([ok, fail], max_retries=0)

        with pytest.raises(RuntimeError):
            agent.execute(mock_context)

        ok.rollback.assert_called_once_with(mock_context)

    @patch("src.agents.base_agent.time.sleep")
    def test_rollback_in_reverse_order(self, mock_sleep, mock_context):
        order = []
        s1 = _ok_skill("first")
        s2 = _ok_skill("second")
        s3 = _fail_skill("third")

        s1.rollback.side_effect = lambda ctx: order.append("s1_rollback")
        s2.rollback.side_effect = lambda ctx: order.append("s2_rollback")

        agent = BaseAgent([s1, s2, s3], max_retries=0)
        with pytest.raises(RuntimeError):
            agent.execute(mock_context)

        assert order == ["s2_rollback", "s1_rollback"]

    @patch("src.agents.base_agent.time.sleep")
    def test_rollback_failure_does_not_mask_original_error(self, mock_sleep, mock_context):
        ok = _ok_skill()
        ok.rollback.side_effect = RuntimeError("rollback também falhou")
        fail = _fail_skill()

        agent = BaseAgent([ok, fail], max_retries=0)

        # Deve levantar o erro original (fail_skill), não o de rollback
        with pytest.raises(RuntimeError, match="fail_skill"):
            agent.execute(mock_context)


# ── Retry ─────────────────────────────────────────────────────────────────────

class TestBaseAgentRetry:
    @patch("src.agents.base_agent.time.sleep")
    def test_retries_on_failure(self, mock_sleep, mock_context):
        skill = _ok_skill()
        # Falha nas 2 primeiras tentativas, sucede na terceira
        skill.execute.side_effect = [
            SkillResult.fail("tentativa 1"),
            SkillResult.fail("tentativa 2"),
            SkillResult.ok("ok na 3ª"),
        ]

        agent = BaseAgent([skill], max_retries=2)
        results = agent.execute(mock_context)

        assert results[0].success is True
        assert skill.execute.call_count == 3

    @patch("src.agents.base_agent.time.sleep")
    def test_raises_after_all_retries_exhausted(self, mock_sleep, mock_context):
        skill = _fail_skill()
        agent = BaseAgent([skill], max_retries=1)

        with pytest.raises(RuntimeError):
            agent.execute(mock_context)

        # 1 tentativa inicial + 1 retry = 2 chamadas
        assert skill.execute.call_count == 2
