"""APIFootballPlayersExtractor — /fixtures/players → bronze.football_players_stats_raw."""

from __future__ import annotations

import structlog

from src.core.context import ExecutionContext
from src.core.exceptions import MCPValidationError
from src.core.result import SkillResult
from src.core.skill_registry import register_skill

from .api_football_base import APIFootballBaseSkill

logger = structlog.get_logger(__name__)

_TABLE = "football_players_stats_raw"
_ENDPOINT = "fixtures/players"


@register_skill
class APIFootballPlayersExtractor(APIFootballBaseSkill):
    """Extrai estatísticas de jogadores por partida para a Bronze."""

    @property
    def name(self) -> str:
        return "api_football_players_extractor"

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

        log.info("players_extraction_start", fixtures=len(fixture_ids))
        total = 0

        try:
            for fixture_id in fixture_ids:
                records, _ = self._make_request(
                    _ENDPOINT, {"fixture": fixture_id}, context
                )
                total += self._write_to_bronze(records, _TABLE, _ENDPOINT, context)

            return SkillResult.ok(
                f"Extraídas stats de jogadores de {len(fixture_ids)} fixtures ({total} registros)",
                rows_affected=total,
            )
        except Exception as exc:
            log.error("players_extraction_failed", error=str(exc))
            return SkillResult.fail(f"Falha na extração de players: {exc}", error=exc)
