"""
Testes para as Processing Skills baseadas em Databricks Jobs SDK.

Estratégia:
- validate()  → testa direto, sem Databricks real
- execute()   → mocka WorkspaceClient inteiro via patch
- Polling     → simula RUNNING → TERMINATED/SUCCESS ou FAILED
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import MCPExecutionError, MCPValidationError
from src.skills.processing import (
    DatabricksEventsNormalize,
    DatabricksFixturesFlatten,
    DatabricksOddsNormalize,
    DatabricksOptimize,
    DatabricksStandingsFlatten,
    DatabricksStatisticsFlatten,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_run(lifecycle, result_state=None, message=""):
    """Cria um mock de run do Databricks SDK."""
    state = MagicMock()
    state.life_cycle_state = lifecycle
    state.result_state = result_state
    state.state_message = message
    run = MagicMock()
    run.state = state
    return run


def _make_ws(lifecycle, result_state, run_id=42, rows=10):
    """
    WorkspaceClient mockado que já retorna TERMINATED na primeira poll.
    Elimina o sleep real substituindo _POLL_INTERVAL_S por 0.
    """
    ws = MagicMock()
    ws.jobs.submit.return_value.run_id = run_id
    ws.jobs.get_run.return_value = _make_run(lifecycle, result_state)

    # Simula notebook.exit JSON com rows_affected
    output = MagicMock()
    output.notebook_output.result = json.dumps({"rows_affected": rows, "status": "success"})
    ws.jobs.get_run_output.return_value = output
    return ws


# ── Fixtures compartilhados ───────────────────────────────────────────────────

@pytest.fixture
def ctx_with_databricks(mock_context):
    mock_context.databricks_host = "https://dbc-test.cloud.databricks.com"
    mock_context.databricks_token = "dapiTEST"
    return mock_context


# ── DatabricksFixturesFlatten ─────────────────────────────────────────────────

class TestDatabricksFixturesFlatten:
    skill = DatabricksFixturesFlatten

    def test_name(self):
        assert self.skill().name == "databricks_fixtures_flatten"

    def test_version(self):
        assert self.skill().version == "1.0.0"

    def test_notebook_path(self):
        assert "bronze_to_silver_fixtures" in self.skill().notebook_path

    def test_validate_fails_without_host(self, empty_context):
        with pytest.raises(MCPValidationError, match="databricks_host"):
            self.skill().validate(empty_context)

    def test_validate_fails_without_token(self, mock_context):
        mock_context.databricks_host = "https://dbc.cloud.databricks.com"
        mock_context.databricks_token = None
        with pytest.raises(MCPValidationError, match="databricks_token"):
            self.skill().validate(mock_context)

    def test_validate_passes(self, ctx_with_databricks):
        assert self.skill().validate(ctx_with_databricks) is True

    def test_execute_success(self, ctx_with_databricks):
        from databricks.sdk.service.jobs import RunLifeCycleState, RunResultState

        ws = _make_ws(RunLifeCycleState.TERMINATED, RunResultState.SUCCESS, rows=50)
        with (
            patch("src.skills.processing.databricks_job_base.WorkspaceClient", return_value=ws),
            patch("src.skills.processing.databricks_job_base._POLL_INTERVAL_S", 0),
        ):
            result = self.skill().execute(ctx_with_databricks)

        assert result.success is True
        assert result.rows_affected == 50

    def test_execute_fails_when_job_fails(self, ctx_with_databricks):
        from databricks.sdk.service.jobs import RunLifeCycleState, RunResultState

        ws = _make_ws(RunLifeCycleState.TERMINATED, RunResultState.FAILED)
        with (
            patch("src.skills.processing.databricks_job_base.WorkspaceClient", return_value=ws),
            patch("src.skills.processing.databricks_job_base._POLL_INTERVAL_S", 0),
        ):
            result = self.skill().execute(ctx_with_databricks)

        assert result.success is False

    def test_execute_raises_on_submit_error(self, ctx_with_databricks):
        ws = MagicMock()
        ws.jobs.submit.side_effect = Exception("network error")
        with (
            patch("src.skills.processing.databricks_job_base.WorkspaceClient", return_value=ws),
        ):
            with pytest.raises(MCPExecutionError):
                self.skill().execute(ctx_with_databricks)

    def test_registered_in_registry(self):
        from src.core.skill_registry import SkillRegistry
        assert "databricks_fixtures_flatten" in SkillRegistry()


# ── DatabricksStatisticsFlatten ───────────────────────────────────────────────

class TestDatabricksStatisticsFlatten:
    skill = DatabricksStatisticsFlatten

    def test_name(self):
        assert self.skill().name == "databricks_statistics_flatten"

    def test_notebook_path(self):
        assert "bronze_to_silver_statistics" in self.skill().notebook_path

    def test_validate_fails_without_credentials(self, empty_context):
        with pytest.raises(MCPValidationError):
            self.skill().validate(empty_context)

    def test_execute_success(self, ctx_with_databricks):
        from databricks.sdk.service.jobs import RunLifeCycleState, RunResultState

        ws = _make_ws(RunLifeCycleState.TERMINATED, RunResultState.SUCCESS, rows=22)
        with (
            patch("src.skills.processing.databricks_job_base.WorkspaceClient", return_value=ws),
            patch("src.skills.processing.databricks_job_base._POLL_INTERVAL_S", 0),
        ):
            result = self.skill().execute(ctx_with_databricks)

        assert result.success is True
        assert result.rows_affected == 22

    def test_registered_in_registry(self):
        from src.core.skill_registry import SkillRegistry
        assert "databricks_statistics_flatten" in SkillRegistry()


# ── DatabricksEventsNormalize ─────────────────────────────────────────────────

class TestDatabricksEventsNormalize:
    skill = DatabricksEventsNormalize

    def test_name(self):
        assert self.skill().name == "databricks_events_normalize"

    def test_notebook_path(self):
        assert "bronze_to_silver_events" in self.skill().notebook_path

    def test_execute_passes_fixture_ids(self, ctx_with_databricks):
        """Fixture IDs armazenados em artifacts devem chegar como parâmetro."""
        from databricks.sdk.service.jobs import RunLifeCycleState, RunResultState

        ctx_with_databricks.set_artifact("fixture_ids", [101, 202])
        ws = _make_ws(RunLifeCycleState.TERMINATED, RunResultState.SUCCESS, rows=5)

        with (
            patch("src.skills.processing.databricks_job_base.WorkspaceClient", return_value=ws),
            patch("src.skills.processing.databricks_job_base._POLL_INTERVAL_S", 0),
        ):
            result = self.skill().execute(ctx_with_databricks)

        assert result.success is True
        # Verifica que fixture_ids foi incluído nos parâmetros do notebook
        call_kwargs = ws.jobs.submit.call_args
        tasks = call_kwargs.kwargs["tasks"]
        nb_params = tasks[0]["notebook_task"]["base_parameters"]
        assert "fixture_ids" in nb_params
        assert nb_params["fixture_ids"] == "101,202"

    def test_registered_in_registry(self):
        from src.core.skill_registry import SkillRegistry
        assert "databricks_events_normalize" in SkillRegistry()


# ── DatabricksOddsNormalize ───────────────────────────────────────────────────

class TestDatabricksOddsNormalize:
    skill = DatabricksOddsNormalize

    def test_name(self):
        assert self.skill().name == "databricks_odds_normalize"

    def test_notebook_path(self):
        assert "bronze_to_silver_odds" in self.skill().notebook_path

    def test_execute_success(self, ctx_with_databricks):
        from databricks.sdk.service.jobs import RunLifeCycleState, RunResultState

        ws = _make_ws(RunLifeCycleState.TERMINATED, RunResultState.SUCCESS, rows=300)
        with (
            patch("src.skills.processing.databricks_job_base.WorkspaceClient", return_value=ws),
            patch("src.skills.processing.databricks_job_base._POLL_INTERVAL_S", 0),
        ):
            result = self.skill().execute(ctx_with_databricks)

        assert result.success is True
        assert result.rows_affected == 300

    def test_registered_in_registry(self):
        from src.core.skill_registry import SkillRegistry
        assert "databricks_odds_normalize" in SkillRegistry()


# ── DatabricksStandingsFlatten ────────────────────────────────────────────────

class TestDatabricksStandingsFlatten:
    skill = DatabricksStandingsFlatten

    def test_name(self):
        assert self.skill().name == "databricks_standings_flatten"

    def test_notebook_path(self):
        assert "bronze_to_silver_standings" in self.skill().notebook_path

    def test_execute_success(self, ctx_with_databricks):
        from databricks.sdk.service.jobs import RunLifeCycleState, RunResultState

        ws = _make_ws(RunLifeCycleState.TERMINATED, RunResultState.SUCCESS, rows=20)
        with (
            patch("src.skills.processing.databricks_job_base.WorkspaceClient", return_value=ws),
            patch("src.skills.processing.databricks_job_base._POLL_INTERVAL_S", 0),
        ):
            result = self.skill().execute(ctx_with_databricks)

        assert result.success is True

    def test_registered_in_registry(self):
        from src.core.skill_registry import SkillRegistry
        assert "databricks_standings_flatten" in SkillRegistry()


# ── DatabricksOptimize ────────────────────────────────────────────────────────

class TestDatabricksOptimize:
    skill = DatabricksOptimize

    def test_name(self):
        assert self.skill().name == "databricks_optimize"

    def test_notebook_path(self):
        assert "optimize_tables" in self.skill().notebook_path

    def test_timeout_is_1_hour(self):
        assert self.skill().timeout_s == 3600

    def test_execute_passes_layer_param(self, ctx_with_databricks):
        from databricks.sdk.service.jobs import RunLifeCycleState, RunResultState

        ws = _make_ws(RunLifeCycleState.TERMINATED, RunResultState.SUCCESS, rows=6)
        with (
            patch("src.skills.processing.databricks_job_base.WorkspaceClient", return_value=ws),
            patch("src.skills.processing.databricks_job_base._POLL_INTERVAL_S", 0),
        ):
            result = self.skill().execute(ctx_with_databricks)

        assert result.success is True
        call_kwargs = ws.jobs.submit.call_args
        tasks = call_kwargs.kwargs["tasks"]
        nb_params = tasks[0]["notebook_task"]["base_parameters"]
        assert nb_params.get("layer") == "silver"

    def test_registered_in_registry(self):
        from src.core.skill_registry import SkillRegistry
        assert "databricks_optimize" in SkillRegistry()


# ── DatabricksJobBaseSkill — comportamentos genéricos ─────────────────────────

class TestDatabricksJobBaseSkillBehaviors:
    """Testa comportamentos do base: timeout, catalog fixo, run_id no payload."""

    def test_always_sends_catalog_football_prediction(self, ctx_with_databricks):
        from databricks.sdk.service.jobs import RunLifeCycleState, RunResultState

        ws = _make_ws(RunLifeCycleState.TERMINATED, RunResultState.SUCCESS)
        with (
            patch("src.skills.processing.databricks_job_base.WorkspaceClient", return_value=ws),
            patch("src.skills.processing.databricks_job_base._POLL_INTERVAL_S", 0),
        ):
            DatabricksFixturesFlatten().execute(ctx_with_databricks)

        tasks = ws.jobs.submit.call_args.kwargs["tasks"]
        params = tasks[0]["notebook_task"]["base_parameters"]
        assert params["catalog"] == "football_prediction"

    def test_always_sends_run_id(self, ctx_with_databricks):
        from databricks.sdk.service.jobs import RunLifeCycleState, RunResultState

        ws = _make_ws(RunLifeCycleState.TERMINATED, RunResultState.SUCCESS)
        with (
            patch("src.skills.processing.databricks_job_base.WorkspaceClient", return_value=ws),
            patch("src.skills.processing.databricks_job_base._POLL_INTERVAL_S", 0),
        ):
            DatabricksFixturesFlatten().execute(ctx_with_databricks)

        tasks = ws.jobs.submit.call_args.kwargs["tasks"]
        params = tasks[0]["notebook_task"]["base_parameters"]
        assert "run_id" in params
        assert params["run_id"] == ctx_with_databricks.run_id

    def test_timeout_returns_fail(self, ctx_with_databricks):
        """Se o job não terminar dentro do timeout, retorna SkillResult.fail."""
        from databricks.sdk.service.jobs import RunLifeCycleState

        # get_run sempre retorna RUNNING — nunca termina
        ws = MagicMock()
        ws.jobs.submit.return_value.run_id = 99
        ws.jobs.get_run.return_value = _make_run(RunLifeCycleState.RUNNING)

        skill = DatabricksFixturesFlatten()
        with (
            patch("src.skills.processing.databricks_job_base.WorkspaceClient", return_value=ws),
            patch("src.skills.processing.databricks_job_base._POLL_INTERVAL_S", 0),
            patch.object(type(skill), "timeout_s", new=0),   # timeout=0 → sai imediatamente
        ):
            result = skill.execute(ctx_with_databricks)

        assert result.success is False
        assert "timeout" in result.message.lower()

    def test_result_contains_databricks_run_id(self, ctx_with_databricks):
        from databricks.sdk.service.jobs import RunLifeCycleState, RunResultState

        ws = _make_ws(RunLifeCycleState.TERMINATED, RunResultState.SUCCESS, run_id=777)
        with (
            patch("src.skills.processing.databricks_job_base.WorkspaceClient", return_value=ws),
            patch("src.skills.processing.databricks_job_base._POLL_INTERVAL_S", 0),
        ):
            result = DatabricksFixturesFlatten().execute(ctx_with_databricks)

        assert result.data["databricks_run_id"] == 777
