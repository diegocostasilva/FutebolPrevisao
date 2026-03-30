"""DatabricksEventsNormalize — Bronze→Silver para eventos de partida."""

from __future__ import annotations

from src.core.context import ExecutionContext
from src.core.skill_registry import register_skill

from .databricks_job_base import DatabricksJobBaseSkill


@register_skill
class DatabricksEventsNormalize(DatabricksJobBaseSkill):
    """Dispara notebook Bronze→Silver de events no cluster Databricks."""

    @property
    def name(self) -> str:
        return "databricks_events_normalize"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def notebook_path(self) -> str:
        return "/databricks/notebooks/silver/bronze_to_silver_events"

    def execute(self, context: ExecutionContext):
        params = {}
        fixture_ids = context.get_artifact("fixture_ids") or []
        if fixture_ids:
            params["fixture_ids"] = ",".join(str(x) for x in fixture_ids)
        return self._run_notebook(context, extra_params=params)
