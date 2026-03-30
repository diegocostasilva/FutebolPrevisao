"""
DatabricksFixturesFlatten — executa notebook Bronze→Silver para fixtures.

Notebook: /databricks/notebooks/silver/bronze_to_silver_fixtures
Resultado: football_prediction.silver.football_fixtures (MERGE upsert)
"""

from __future__ import annotations

from src.core.context import ExecutionContext
from src.core.skill_registry import register_skill

from .databricks_job_base import DatabricksJobBaseSkill


@register_skill
class DatabricksFixturesFlatten(DatabricksJobBaseSkill):
    """Dispara notebook Bronze→Silver de fixtures no cluster Databricks."""

    @property
    def name(self) -> str:
        return "databricks_fixtures_flatten"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def notebook_path(self) -> str:
        return "/databricks/notebooks/silver/bronze_to_silver_fixtures"

    def execute(self, context: ExecutionContext):
        return self._run_notebook(context)

    def _build_notebook_params(self, context: ExecutionContext) -> dict:
        params = super()._build_notebook_params(context)
        params["ingestion_date"] = (
            context.get_artifact("fixtures_from_date") or ""
        )
        return params
