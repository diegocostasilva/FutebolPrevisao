"""
APIFootballQuotaMonitor — monitora consumo de quota da API-Football.

Lê os valores de quota armazenados nos artifacts pelas Skills anteriores
e registra métricas de uso. Não faz chamadas HTTP próprias.
"""

from __future__ import annotations

import structlog

from src.core.context import ExecutionContext
from src.core.result import SkillResult
from src.core.skill_base import MCPSkill
from src.core.skill_registry import register_skill

logger = structlog.get_logger(__name__)


@register_skill
class APIFootballQuotaMonitor(MCPSkill):
    """
    Skill de monitoramento de quota — deve ser executada por último no IngestionAgent.

    Lê quota_remaining e quota_limit dos artifacts (preenchidos por _check_quota
    das Skills anteriores) e classifica o estado de consumo.
    """

    @property
    def name(self) -> str:
        return "api_football_quota_monitor"

    @property
    def version(self) -> str:
        return "1.0.0"

    def validate(self, context: ExecutionContext) -> bool:
        return True  # Sempre pode rodar — apenas lê artifacts

    def execute(self, context: ExecutionContext) -> SkillResult:
        log = logger.bind(skill=self.name, run_id=context.run_id)

        remaining: int = context.get_artifact("quota_remaining", 0)
        limit: int = context.get_artifact("quota_limit", 0)
        quota_critical: bool = context.get_artifact("quota_critical", False)

        if limit == 0:
            return SkillResult.ok(
                "Nenhuma informação de quota disponível nos artifacts",
                data={"quota_remaining": None, "quota_limit": None},
            )

        consumed = limit - remaining
        pct = consumed / limit * 100

        status = "ok"
        if quota_critical or pct >= 95:
            status = "critical"
            log.error("quota_critical", remaining=remaining, limit=limit, pct=pct)
        elif pct >= 80:
            status = "warning"
            log.warning("quota_high", remaining=remaining, limit=limit, pct=pct)
        else:
            log.info("quota_ok", remaining=remaining, limit=limit, pct=pct)

        return SkillResult.ok(
            f"Quota: {remaining}/{limit} restantes ({100 - pct:.1f}% disponível) — {status}",
            rows_affected=0,
            data={
                "quota_remaining": remaining,
                "quota_limit": limit,
                "quota_consumed_pct": round(pct, 2),
                "quota_status": status,
            },
        )
