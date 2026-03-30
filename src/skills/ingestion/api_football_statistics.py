"""APIFootballStatisticsExtractor — /fixtures/statistics → bronze.football_statistics_raw."""

from __future__ import annotations

import structlog

from src.core.context import ExecutionContext
from src.core.exceptions import MCPValidationError
from src.core.result import SkillResult
from src.core.skill_registry import register_skill

from .api_football_base import APIFootballBaseSkill

logger = structlog.get_logger(__name__)

_TABLE = "football_statistics_raw"
_ENDPOINT = "fixtures/statistics"


@register_skill
class APIFootballStatisticsExtractor(APIFootballBaseSkill):
    """Extrai estatísticas de partida para a Bronze. Depende de fixture_ids no artifacts."""

    @property
    def name(self) -> str:
        return "api_football_statistics_extractor"

    @property
    def version(self) -> str:
        return "1.0.0"

    def validate(self, context: ExecutionContext) -> bool:
        super().validate(context)
        if not context.get_artifact("fixture_ids") and not context.params.get("fixture_ids"):
            raise MCPValidationError(
                "fixture_ids ausente nos artifacts e nos params",
                skill_name=self.name,
            )
        return True

    def execute(self, context: ExecutionContext) -> SkillResult:
        log = logger.bind(skill=self.name, run_id=context.run_id)

        fixture_ids: list[int] = (
            context.get_artifact("fixture_ids")
            or context.params.get("fixture_ids", [])
        )

        log.info("statistics_extraction_start", fixtures=len(fixture_ids))
        total = 0

        try:
            for fixture_id in fixture_ids:
                records, _ = self._make_request(
                    _ENDPOINT, {"fixture": fixture_id}, context
                )
                total += self._write_to_bronze(records, _TABLE, _ENDPOINT, context)

            return SkillResult.ok(
                f"Extraídas statistics de {total} registros ({len(fixture_ids)} fixtures)",
                rows_affected=total,
            )
        except Exception as exc:
            log.error("statistics_extraction_failed", error=str(exc))
            return SkillResult.fail(f"Falha na extração de statistics: {exc}", error=exc)
