"""APIFootballOddsExtractor — /odds → bronze.football_odds_raw."""

from __future__ import annotations

import structlog

from src.core.context import ExecutionContext
from src.core.exceptions import MCPValidationError
from src.core.result import SkillResult
from src.core.skill_registry import register_skill

from .api_football_base import APIFootballBaseSkill

logger = structlog.get_logger(__name__)

_TABLE = "football_odds_raw"
_ENDPOINT = "odds"

# Mercados de interesse: Match Winner (1X2), Over/Under 2.5, Both Teams Score
_BET_IDS = {1, 5, 8}


@register_skill
class APIFootballOddsExtractor(APIFootballBaseSkill):
    """
    Extrai odds pré-jogo para a Bronze.

    Coleta mercados: Match Winner (1), Over/Under 2.5 (5), BTTS (8).
    Filtra apenas fixtures presentes nos artifacts (coletados pela FixturesSkill).
    """

    @property
    def name(self) -> str:
        return "api_football_odds_extractor"

    @property
    def version(self) -> str:
        return "1.0.0"

    def validate(self, context: ExecutionContext) -> bool:
        super().validate(context)
        if not context.league_ids:
            raise MCPValidationError(
                "league_ids não definido nos params",
                skill_name=self.name,
            )
        return True

    def execute(self, context: ExecutionContext) -> SkillResult:
        log = logger.bind(skill=self.name, run_id=context.run_id)

        fixture_ids: list[int] = (
            context.get_artifact("fixture_ids")
            or context.params.get("fixture_ids", [])
        )

        log.info("odds_extraction_start", fixtures=len(fixture_ids))
        total = 0

        try:
            for fixture_id in fixture_ids:
                for bet_id in _BET_IDS:
                    records, _ = self._make_request(
                        _ENDPOINT,
                        {"fixture": fixture_id, "bet": bet_id},
                        context,
                    )
                    total += self._write_to_bronze(records, _TABLE, _ENDPOINT, context)

            return SkillResult.ok(
                f"Extraídas odds de {len(fixture_ids)} fixtures ({total} registros)",
                rows_affected=total,
            )
        except Exception as exc:
            log.error("odds_extraction_failed", error=str(exc))
            return SkillResult.fail(f"Falha na extração de odds: {exc}", error=exc)
