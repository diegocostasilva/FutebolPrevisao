"""Testes para src/skills/ingestion/api_football_fixtures.py"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import MCPValidationError
from src.skills.ingestion.api_football_fixtures import APIFootballFixturesExtractor


@pytest.fixture
def skill() -> APIFootballFixturesExtractor:
    return APIFootballFixturesExtractor()


# ── Registro ──────────────────────────────────────────────────────────────────

class TestRegistration:
    def test_name(self, skill):
        assert skill.name == "api_football_fixtures_extractor"

    def test_version(self, skill):
        assert skill.version == "1.0.0"

    def test_registered_in_registry(self):
        from src.core.skill_registry import SkillRegistry
        assert "api_football_fixtures_extractor" in SkillRegistry()


# ── validate ──────────────────────────────────────────────────────────────────

class TestValidate:
    def test_passes_with_key_and_leagues(self, skill, mock_context):
        assert skill.validate(mock_context) is True

    def test_fails_without_api_key(self, skill, empty_context):
        with pytest.raises(MCPValidationError):
            skill.validate(empty_context)

    def test_fails_with_empty_league_ids(self, skill, mock_context):
        mock_context.params["league_ids"] = []
        with pytest.raises(MCPValidationError, match="league_ids"):
            skill.validate(mock_context)


# ── _resolve_dates ─────────────────────────────────────────────────────────────

class TestResolveDates:
    def test_incremental_uses_yesterday_today(self, skill, mock_context):
        mock_context.params["mode"] = "incremental"
        today = date.today().isoformat()

        from_d, to_d = skill._resolve_dates(mock_context)

        assert to_d == today
        assert from_d <= today

    def test_backfill_uses_params_dates(self, skill, mock_context):
        mock_context.params["mode"] = "backfill"
        mock_context.params["from_date"] = "2025-01-01"
        mock_context.params["to_date"] = "2025-01-31"

        from_d, to_d = skill._resolve_dates(mock_context)

        assert from_d == "2025-01-01"
        assert to_d == "2025-01-31"

    def test_backfill_raises_without_dates(self, skill, mock_context):
        mock_context.params["mode"] = "backfill"
        mock_context.params.pop("from_date", None)
        mock_context.params.pop("to_date", None)

        with pytest.raises(MCPValidationError, match="from_date"):
            skill._resolve_dates(mock_context)


# ── execute ───────────────────────────────────────────────────────────────────

class TestExecute:
    @patch.object(APIFootballFixturesExtractor, "_make_request")
    @patch.object(APIFootballFixturesExtractor, "_write_to_bronze")
    def test_stores_fixture_ids_in_artifacts(
        self, mock_write, mock_request, skill, mock_context
    ):
        # mock_context tem 2 ligas ([71, 72]); cada liga retorna 1 fixture diferente
        mock_request.side_effect = [
            ([{"fixture": {"id": 100}}], {}),
            ([{"fixture": {"id": 101}}], {}),
        ]
        mock_write.return_value = 1

        result = skill.execute(mock_context)

        assert result.success is True
        assert mock_context.get_artifact("fixture_ids") == [100, 101]

    @patch.object(APIFootballFixturesExtractor, "_make_request")
    @patch.object(APIFootballFixturesExtractor, "_write_to_bronze")
    def test_calls_make_request_per_league(
        self, mock_write, mock_request, skill, mock_context
    ):
        mock_request.return_value = ([], {})
        mock_write.return_value = 0

        skill.execute(mock_context)

        assert mock_request.call_count == len(mock_context.league_ids)

    @patch.object(APIFootballFixturesExtractor, "_make_request")
    def test_returns_fail_on_exception(self, mock_request, skill, mock_context):
        mock_request.side_effect = RuntimeError("API down")

        result = skill.execute(mock_context)

        assert result.success is False
        assert "API down" in result.message

    @patch.object(APIFootballFixturesExtractor, "_make_request")
    @patch.object(APIFootballFixturesExtractor, "_write_to_bronze")
    def test_rows_affected_is_total_written(
        self, mock_write, mock_request, skill, mock_context
    ):
        mock_request.return_value = ([{"fixture": {"id": 1}}], {})
        mock_write.return_value = 5  # simula 5 rows por liga

        result = skill.execute(mock_context)

        # 2 ligas × 5 rows = 10
        assert result.rows_affected == 10
