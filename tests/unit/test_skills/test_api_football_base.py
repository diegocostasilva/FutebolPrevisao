"""Testes para src/skills/ingestion/api_football_base.py"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.core.context import ExecutionContext
from src.core.exceptions import MCPExecutionError, MCPQuotaExceededError, MCPValidationError
from src.skills.ingestion.api_football_base import APIFootballBaseSkill


# ── Implementação concreta mínima para testar a base ─────────────────────────

class _ConcreteSkill(APIFootballBaseSkill):
    @property
    def name(self) -> str:
        return "test_base_skill"

    @property
    def version(self) -> str:
        return "1.0.0"

    def validate(self, context: ExecutionContext) -> bool:
        return super().validate(context)

    def execute(self, context: ExecutionContext):
        from src.core.result import SkillResult
        return SkillResult.ok("ok")


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def skill() -> _ConcreteSkill:
    return _ConcreteSkill()


@pytest.fixture
def mock_response():
    resp = MagicMock()
    resp.status_code = 200
    resp.ok = True
    resp.json.return_value = {
        "response": [{"fixture": {"id": 1}}, {"fixture": {"id": 2}}]
    }
    resp.headers = {
        "x-ratelimit-requests-remaining": "900",
        "x-ratelimit-requests-limit": "1000",
    }
    resp.raise_for_status = MagicMock()
    return resp


# ── validate ──────────────────────────────────────────────────────────────────

class TestValidate:
    def test_passes_with_api_key(self, skill, mock_context):
        assert skill.validate(mock_context) is True

    def test_raises_without_api_key(self, skill, empty_context):
        with pytest.raises(MCPValidationError, match="api_football_key"):
            skill.validate(empty_context)


# ── _make_request ─────────────────────────────────────────────────────────────

class TestMakeRequest:
    @patch("src.skills.ingestion.api_football_base.requests.get")
    @patch("src.skills.ingestion.api_football_base.time.sleep")
    def test_returns_response_list(self, mock_sleep, mock_get, skill, mock_response, mock_context):
        mock_get.return_value = mock_response

        records, headers = skill._make_request("fixtures", {"league": 71}, mock_context)

        assert len(records) == 2
        assert records[0]["fixture"]["id"] == 1

    @patch("src.skills.ingestion.api_football_base.requests.get")
    @patch("src.skills.ingestion.api_football_base.time.sleep")
    def test_sets_auth_header(self, mock_sleep, mock_get, skill, mock_response, mock_context):
        mock_get.return_value = mock_response

        skill._make_request("fixtures", {}, mock_context)

        _, kwargs = mock_get.call_args
        assert kwargs["headers"]["x-apisports-key"] == mock_context.api_football_key

    @patch("src.skills.ingestion.api_football_base.requests.get")
    @patch("src.skills.ingestion.api_football_base.time.sleep")
    def test_raises_on_non_ok_status(self, mock_sleep, mock_get, skill, mock_context):
        bad_resp = MagicMock()
        bad_resp.status_code = 401
        bad_resp.ok = False
        bad_resp.raise_for_status = MagicMock()
        mock_get.return_value = bad_resp

        with pytest.raises(MCPExecutionError):
            skill._make_request("fixtures", {}, mock_context)


# ── _check_quota ──────────────────────────────────────────────────────────────

class TestCheckQuota:
    def test_raises_when_remaining_zero(self, skill, mock_context):
        headers = {"x-ratelimit-requests-remaining": "0", "x-ratelimit-requests-limit": "1000"}
        with pytest.raises(MCPQuotaExceededError):
            skill._check_quota(headers, mock_context)

    def test_sets_quota_critical_at_95_pct(self, skill, mock_context):
        headers = {"x-ratelimit-requests-remaining": "30", "x-ratelimit-requests-limit": "1000"}
        skill._check_quota(headers, mock_context)
        assert mock_context.get_artifact("quota_critical") is True

    def test_ok_below_80_pct(self, skill, mock_context):
        headers = {"x-ratelimit-requests-remaining": "900", "x-ratelimit-requests-limit": "1000"}
        skill._check_quota(headers, mock_context)
        assert mock_context.get_artifact("quota_critical") is None

    def test_stores_remaining_in_artifacts(self, skill, mock_context):
        headers = {"x-ratelimit-requests-remaining": "500", "x-ratelimit-requests-limit": "1000"}
        skill._check_quota(headers, mock_context)
        assert mock_context.get_artifact("quota_remaining") == 500

    def test_ignores_missing_headers(self, skill, mock_context):
        """Sem headers de quota não deve levantar exceção."""
        skill._check_quota({}, mock_context)


# ── _write_to_bronze ──────────────────────────────────────────────────────────

class TestWriteToBronze:
    def test_returns_zero_for_empty_records(self, skill, mock_context):
        result = skill._write_to_bronze([], "test_table", "fixtures", mock_context)
        assert result == 0

    def test_calls_spark_write(self, skill, mock_context):
        records = [{"id": 1}, {"id": 2}]
        mock_df = MagicMock()
        mock_context.spark_session.createDataFrame.return_value = mock_df

        count = skill._write_to_bronze(records, "football_fixtures_raw", "fixtures", mock_context)

        assert count == 2
        mock_context.spark_session.createDataFrame.assert_called_once()
        mock_df.write.format.assert_called_with("delta")

    def test_raises_without_spark_or_databricks_creds(self, skill, empty_context):
        """Sem SparkSession e sem credenciais Databricks → MCPExecutionError."""
        with pytest.raises(MCPExecutionError, match="databricks_host"):
            skill._write_to_bronze([{"id": 1}], "table", "ep", empty_context)

    def test_uses_sql_connector_when_no_spark(self, skill, mock_context):
        """Sem SparkSession mas com credenciais → usa SQL Connector."""
        mock_context.spark_session = None
        mock_context.databricks_host = "https://dbc-test.cloud.databricks.com"
        mock_context.databricks_token = "dapiTEST"
        mock_context.databricks_http_path = "/sql/1.0/warehouses/abc"

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("databricks.sql.connect", return_value=mock_conn):
            result = skill._write_to_bronze([{"id": 1}], "test_table", "ep", mock_context)

        assert result == 1
        mock_cursor.executemany.assert_called_once()

    def test_adds_metadata_fields(self, skill, mock_context):
        records = [{"id": 1}]
        captured_rows = []

        def capture(rows):
            captured_rows.extend(rows)
            return MagicMock()

        mock_context.spark_session.createDataFrame.side_effect = capture
        skill._write_to_bronze(records, "test_table", "fixtures", mock_context)

        assert len(captured_rows) == 1
        row = captured_rows[0]
        assert "_ingestion_date" in row
        assert "_ingestion_ts" in row
        assert "_batch_id" in row
        assert "_source_endpoint" in row
        assert "payload" in row
