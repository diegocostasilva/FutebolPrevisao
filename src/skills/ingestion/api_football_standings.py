"""APIFootballStandingsExtractor — /standings → bronze.football_standings_raw."""

from __future__ import annotations

import structlog

from src.core.context import ExecutionContext
from src.core.result import SkillResult
from src.core.skill_registry import register_skill

from .api_football_base import APIFootballBaseSkill

logger = structlog.get_logger(__name__)

_TABLE = "football_standings_raw"
_ENDPOINT = "standings"


@register_skill
class APIFootballStandingsExtractor(APIFootballBaseSkill):
    """Extrai classificação por liga/temporada para a Bronze."""

    @property
    def name(self) -> str:
        return "api_football_standings_extractor"

    @property
    def version(self) -> str:
        return "1.0.0"

    def validate(self, context: ExecutionContext) -> bool:
        return super().validate(context)

    def execute(self, context: ExecutionContext) -> SkillResult:
        log = logger.bind(skill=self.name, run_id=context.run_id)

        log.info("standings_extraction_start", leagues=context.league_ids)
        total = 0

        try:
            for league_id in context.league_ids:
                records, _ = self._make_request(
                    _ENDPOINT,
                    {"league": league_id, "season": context.season},
                    context,
                )
                total += self._write_to_bronze(records, _TABLE, _ENDPOINT, context)
                log.info("league_standings_done", league_id=league_id, count=len(records))

            return SkillResult.ok(
                f"Extraída classificação de {len(context.league_ids)} liga(s) ({total} registros)",
                rows_affected=total,
            )
        except Exception as exc:
            log.error("standings_extraction_failed", error=str(exc))
            return SkillResult.fail(f"Falha na extração de standings: {exc}", error=exc)
