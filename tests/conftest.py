"""
Shared pytest fixtures for the Football Prediction Engine test suite.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.core.context import ExecutionContext


@pytest.fixture
def mock_context() -> ExecutionContext:
    """
    Minimal ExecutionContext for unit tests.
    Connections are MagicMocks — no real DB or Spark needed.
    """
    return ExecutionContext(
        run_id="test-run-001",
        execution_date=datetime(2026, 1, 15, 6, 0, 0),
        dag_id="football_daily_pipeline",
        task_id="ingestion_agent",
        environment="dev",
        api_football_key="test-api-key-123",
        databricks_host="https://test.azuredatabricks.net",
        databricks_token="test-token",
        spark_session=MagicMock(),
        pg_connection=MagicMock(),
        params={
            "league_ids": [71, 72],
            "season": 2025,
            "mode": "incremental",
        },
    )


@pytest.fixture
def prod_context() -> ExecutionContext:
    """Context with environment='prod' for testing is_production guard."""
    return ExecutionContext(
        run_id="prod-run-001",
        execution_date=datetime(2026, 1, 15, 6, 0, 0),
        dag_id="football_daily_pipeline",
        task_id="ingestion_agent",
        environment="prod",
        api_football_key="real-api-key",
        params={"league_ids": [71], "season": 2025},
    )


@pytest.fixture
def empty_context() -> ExecutionContext:
    """Bare context with no params — used to test default behaviours."""
    return ExecutionContext(
        run_id="empty-run-001",
        execution_date=datetime(2026, 1, 15),
        dag_id="test_dag",
        task_id="test_task",
        environment="dev",
    )
