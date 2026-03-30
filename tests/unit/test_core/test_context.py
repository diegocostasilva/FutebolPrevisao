"""Tests for src/core/context.py"""

from datetime import datetime

import pytest

from src.core.context import ExecutionContext


class TestExecutionContextDefaults:
    def test_run_id_generated_if_not_provided(self):
        ctx = ExecutionContext(execution_date=datetime(2026, 1, 1))
        assert len(ctx.run_id) == 36  # UUID4 format

    def test_two_instances_get_different_run_ids(self):
        a = ExecutionContext(execution_date=datetime(2026, 1, 1))
        b = ExecutionContext(execution_date=datetime(2026, 1, 1))
        assert a.run_id != b.run_id

    def test_environment_defaults_to_dev(self):
        ctx = ExecutionContext(execution_date=datetime(2026, 1, 1))
        assert ctx.environment == "dev"

    def test_params_defaults_to_empty_dict(self):
        ctx = ExecutionContext(execution_date=datetime(2026, 1, 1))
        assert ctx.params == {}

    def test_artifacts_defaults_to_empty_dict(self):
        ctx = ExecutionContext(execution_date=datetime(2026, 1, 1))
        assert ctx.artifacts == {}


class TestExecutionContextProperties:
    def test_is_production_false_for_dev(self, mock_context):
        assert mock_context.is_production is False

    def test_is_production_true_for_prod(self, prod_context):
        assert prod_context.is_production is True

    def test_league_ids_from_params(self, mock_context):
        assert mock_context.league_ids == [71, 72]

    def test_league_ids_defaults_to_brasileirao(self, empty_context):
        assert empty_context.league_ids == [71]

    def test_season_from_params(self, mock_context):
        assert mock_context.season == 2025

    def test_season_defaults_to_2025(self, empty_context):
        assert empty_context.season == 2025

    def test_mode_from_params(self, mock_context):
        assert mock_context.mode == "incremental"

    def test_mode_defaults_to_incremental(self, empty_context):
        assert empty_context.mode == "incremental"


class TestExecutionContextArtifacts:
    def test_set_and_get_artifact(self, mock_context):
        mock_context.set_artifact("fixture_ids", [1, 2, 3])
        assert mock_context.get_artifact("fixture_ids") == [1, 2, 3]

    def test_get_artifact_returns_default_when_missing(self, mock_context):
        assert mock_context.get_artifact("nonexistent", default=[]) == []

    def test_get_artifact_returns_none_by_default(self, mock_context):
        assert mock_context.get_artifact("missing") is None

    def test_set_artifact_overwrites_existing(self, mock_context):
        mock_context.set_artifact("key", "first")
        mock_context.set_artifact("key", "second")
        assert mock_context.get_artifact("key") == "second"


class TestExecutionContextStr:
    def test_str_contains_dag_id(self, mock_context):
        assert "football_daily_pipeline" in str(mock_context)

    def test_str_contains_environment(self, mock_context):
        assert "dev" in str(mock_context)

    def test_str_contains_season(self, mock_context):
        assert "2025" in str(mock_context)
