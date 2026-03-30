"""DatabricksStandingsFlatten — Bronze→Silver para classificação."""

from __future__ import annotations

from src.core.context import ExecutionContext
from src.core.skill_registry import register_skill

from .databricks_job_base import DatabricksJobBaseSkill


@register_skill
class DatabricksStandingsFlatten(DatabricksJobBaseSkill):
    """Dispara notebook Bronze→Silver de standings no cluster Databricks."""

    @property
    def name(self) -> str:
        return "databricks_standings_flatten"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def notebook_path(self) -> str:
        return "/databricks/notebooks/silver/bronze_to_silver_standings"

    def execute(self, context: ExecutionContext):
        return self._run_notebook(context)
