"""APIFootballLeaguesExtractor — /leagues → bronze.football_leagues_raw.

Extrai metadados de ligas incluindo o campo `coverage`, que indica quais
endpoints a API suporta para cada liga.

Frequência: semanal.
"""

from __future__ import annotations

import structlog

from src.core.context import ExecutionContext
from src.core.result import SkillResult
from src.core.skill_registry import register_skill

from .api_football_base import APIFootballBaseSkill

logger = structlog.get_logger(__name__)

_TABLE = "football_leagues_raw"
_ENDPOINT = "leagues"


@register_skill
class APIFootballLeaguesExtractor(APIFootballBaseSkill):
    """Extrai metadados de ligas (incluindo coverage) para a Bronze."""

    @property
    def name(self) -> str:
        return "api_football_leagues_extractor"

    @property
    def version(self) -> str:
        return "1.0.0"

    def validate(self, context: ExecutionContext) -> bool:
        return super().validate(context)

    def execute(self, context: ExecutionContext) -> SkillResult:
        log = logger.bind(skill=self.name, run_id=context.run_id)

        log.info("leagues_extraction_start", leagues=context.league_ids)
        total = 0

        try:
            for league_id in context.league_ids:
                records, _ = self._make_request(
                    _ENDPOINT,
                    {"id": league_id, "season": context.season},
                    context,
                )
                total += self._write_to_bronze(records, _TABLE, _ENDPOINT, context)

                # Armazena campo coverage nos artifacts para Skills subsequentes
                for record in records:
                    if isinstance(record, dict):
                        coverage = record.get("seasons", [{}])[-1].get("coverage", {})
                        coverages = context.get_artifact("league_coverages") or {}
                        coverages[league_id] = coverage
                        context.set_artifact("league_coverages", coverages)

            return SkillResult.ok(
                f"Extraídos metadados de {len(context.league_ids)} liga(s) ({total} registros)",
                rows_affected=total,
            )
        except Exception as exc:
            log.error("leagues_extraction_failed", error=str(exc))
            return SkillResult.fail(f"Falha na extração de leagues: {exc}", error=exc)
