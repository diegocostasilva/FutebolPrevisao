"""
DatabricksOptimize — executa OPTIMIZE + ZORDER em todas as tabelas Silver.

Substitui as Skills de dedup/key-generator do modelo anterior.
O notebook de manutenção faz OPTIMIZE, ZORDER e VACUUM no cluster Databricks.
"""

from __future__ import annotations

from src.core.context import ExecutionContext
from src.core.skill_registry import register_skill

from .databricks_job_base import DatabricksJobBaseSkill


@register_skill
class DatabricksOptimize(DatabricksJobBaseSkill):
    """Dispara notebook de OPTIMIZE+ZORDER nas tabelas Silver/Gold."""

    @property
    def name(self) -> str:
        return "databricks_optimize"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def notebook_path(self) -> str:
        return "/databricks/notebooks/maintenance/optimize_tables"

    @property
    def timeout_s(self) -> int:
        return 3600  # 1h — manutenção pode demorar

    def execute(self, context: ExecutionContext):
        return self._run_notebook(context, extra_params={"layer": "silver"})
