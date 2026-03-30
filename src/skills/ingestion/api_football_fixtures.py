"""
APIFootballFixturesExtractor — extrai partidas do endpoint /fixtures.

Grava JSON bruto em bronze.football_fixtures_raw.
Armazena lista de fixture_ids em context.artifacts para Skills subsequentes.
"""

from __future__ import annotations

from datetime import date, timedelta

import structlog

from src.core.context import ExecutionContext
from src.core.exceptions import MCPValidationError
from src.core.result import SkillResult
from src.core.skill_registry import register_skill

from .api_football_base import APIFootballBaseSkill

logger = structlog.get_logger(__name__)

_TABLE = "football_fixtures_raw"
_ENDPOINT = "fixtures"


@register_skill
class APIFootballFixturesExtractor(APIFootballBaseSkill):
    """Extrai partidas da API-Football para a Bronze."""

    @property
    def name(self) -> str:
        return "api_football_fixtures_extractor"

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

        mode = context.mode
        season = context.season
        from_date, to_date = self._resolve_dates(context)

        log.info("fixtures_extraction_start", mode=mode, leagues=context.league_ids)

        total_fixtures = 0
        all_fixture_ids: list[int] = []

        try:
            for league_id in context.league_ids:
                params: dict = {
                    "league": league_id,
                    "season": season,
                    "from": from_date,
                    "to": to_date,
                }
                records, _ = self._make_request(_ENDPOINT, params, context)

                written = self._write_to_bronze(records, _TABLE, _ENDPOINT, context)
                total_fixtures += written

                fixture_ids = [
                    r["fixture"]["id"]
                    for r in records
                    if isinstance(r, dict) and "fixture" in r
                ]
                all_fixture_ids.extend(fixture_ids)

                log.info(
                    "league_fixtures_done",
                    league_id=league_id,
                    count=len(records),
                )

            context.set_artifact("fixture_ids", all_fixture_ids)
            context.set_artifact("fixtures_from_date", from_date)
            context.set_artifact("fixtures_to_date", to_date)

            return SkillResult.ok(
                f"Extraídas {total_fixtures} fixtures de {len(context.league_ids)} liga(s)",
                rows_affected=total_fixtures,
                data={"fixture_ids": all_fixture_ids, "from": from_date, "to": to_date},
            )

        except Exception as exc:
            log.error("fixtures_extraction_failed", error=str(exc))
            return SkillResult.fail(
                f"Falha na extração de fixtures: {exc}",
                error=exc,
            )

    def rollback(self, context: ExecutionContext) -> None:
        # Bronze é append-only — não há rollback físico.
        # Registra o batch_id para reprocessamento manual se necessário.
        logger.bind(skill=self.name, run_id=context.run_id).warning(
            "fixtures_rollback_requested",
            note="Bronze é append-only; reprocessar via batch_id se necessário",
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _resolve_dates(self, context: ExecutionContext) -> tuple[str, str]:
        """Resolve from_date / to_date com base no mode (incremental ou backfill)."""
        params = context.params

        if context.mode == "backfill":
            from_date = params.get("from_date", "")
            to_date = params.get("to_date", "")
            if not from_date or not to_date:
                raise MCPValidationError(
                    "Modo backfill requer from_date e to_date nos params",
                    skill_name=self.name,
                )
            return from_date, to_date

        # Incremental: hoje e ontem para capturar partidas que terminaram
        today = date.today()
        yesterday = today - timedelta(days=1)
        from_date = params.get("from_date", yesterday.isoformat())
        to_date = params.get("to_date", today.isoformat())
        return from_date, to_date
