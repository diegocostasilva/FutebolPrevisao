"""APIFootballPredictionsExtractor — /predictions → bronze.football_predictions_raw.

As predições da API são usadas como FEATURES para o modelo próprio,
não como substituto do modelo de ML interno.
"""

from __future__ import annotations

import structlog

from src.core.context import ExecutionContext
from src.core.exceptions import MCPValidationError
from src.core.result import SkillResult
from src.core.skill_registry import register_skill

from .api_football_base import APIFootballBaseSkill

logger = structlog.get_logger(__name__)

_TABLE = "football_predictions_raw"
_ENDPOINT = "predictions"


@register_skill
class APIFootballPredictionsExtractor(APIFootballBaseSkill):
    """Extrai predições da API-Football para a Bronze (usadas como features de ML)."""

    @property
    def name(self) -> str:
        return "api_football_predictions_extractor"

    @property
    def version(self) -> str:
        return "1.0.0"

    def validate(self, context: ExecutionContext) -> bool:
        super().validate(context)
        return True

    def execute(self, context: ExecutionContext) -> SkillResult:
        log = logger.bind(skill=self.name, run_id=context.run_id)

        fixture_ids: list[int] = (
            context.get_artifact("fixture_ids")
            or context.params.get("fixture_ids", [])
        )
        if not fixture_ids:
            return SkillResult.ok("Sem fixture_ids no período — nada a extrair", rows_affected=0)

        log.info("api_predictions_extraction_start", fixtures=len(fixture_ids))
        total = 0

        try:
            for fixture_id in fixture_ids:
                records, _ = self._make_request(
                    _ENDPOINT, {"fixture": fixture_id}, context
                )
                total += self._write_to_bronze(records, _TABLE, _ENDPOINT, context)

            return SkillResult.ok(
                f"Extraídas predições da API de {len(fixture_ids)} fixtures ({total} registros)",
                rows_affected=total,
            )
        except Exception as exc:
            log.error("api_predictions_extraction_failed", error=str(exc))
            return SkillResult.fail(
                f"Falha na extração de predictions: {exc}", error=exc
            )
