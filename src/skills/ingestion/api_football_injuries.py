"""APIFootballInjuriesExtractor — /injuries → bronze.football_injuries_raw."""

from __future__ import annotations

import structlog

from src.core.context import ExecutionContext
from src.core.result import SkillResult
from src.core.skill_registry import register_skill

from .api_football_base import APIFootballBaseSkill

logger = structlog.get_logger(__name__)

_TABLE = "football_injuries_raw"
_ENDPOINT = "injuries"


@register_skill
class APIFootballInjuriesExtractor(APIFootballBaseSkill):
    """Extrai lesões por liga/temporada para a Bronze."""

    @property
    def name(self) -> str:
        return "api_football_injuries_extractor"

    @property
    def version(self) -> str:
        return "1.0.0"

    def validate(self, context: ExecutionContext) -> bool:
        return super().validate(context)

    def execute(self, context: ExecutionContext) -> SkillResult:
        log = logger.bind(skill=self.name, run_id=context.run_id)

        log.info("injuries_extraction_start", leagues=context.league_ids)
        total = 0

        try:
            for league_id in context.league_ids:
                records, _ = self._make_request(
                    _ENDPOINT,
                    {"league": league_id, "season": context.season},
                    context,
                )
                total += self._write_to_bronze(records, _TABLE, _ENDPOINT, context)

            return SkillResult.ok(
                f"Extraídas lesões de {len(context.league_ids)} liga(s) ({total} registros)",
                rows_affected=total,
            )
        except Exception as exc:
            log.error("injuries_extraction_failed", error=str(exc))
            return SkillResult.fail(f"Falha na extração de injuries: {exc}", error=exc)
