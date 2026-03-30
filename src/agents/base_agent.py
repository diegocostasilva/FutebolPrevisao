"""
BaseAgent — padrão de execução, retry e logging para todos os Agents.

Contrato (PRD_ORIENTACAO_AGENTE_IA.md):
  - Agents são orquestradores: recebem lista de Skills e as executam em ordem.
  - Fail-fast: primeira Skill que falhar interrompe a execução e aciona rollback.
  - Airflow nunca executa lógica de negócio — apenas chama Agent.execute().
  - Logging via structlog com run_id em todos os registros.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from src.core.context import ExecutionContext
from src.core.result import SkillResult
from src.core.skill_base import MCPSkill

logger = structlog.get_logger(__name__)


class BaseAgent:
    """
    Orquestrador base para uma sequência de MCPSkills.

    Fluxo por Skill:
        1. log início
        2. validate(context) — levanta exceção se inválido
        3. execute(context) com retry e backoff
        4. log resultado
        5. Se falhou → rollback + RuntimeError (fail-fast)

    Args:
        skills:      Lista de Skills na ordem de execução.
        max_retries: Número máximo de tentativas por Skill (default 2).
    """

    def __init__(self, skills: list[MCPSkill], max_retries: int = 2) -> None:
        self.skills = skills
        self.max_retries = max_retries

    # ── Nome do agent (para logging) ──────────────────────────────────────────

    @property
    def agent_name(self) -> str:
        return self.__class__.__name__

    # ── Execução principal ────────────────────────────────────────────────────

    def execute(self, context: ExecutionContext) -> list[SkillResult]:
        """
        Executa todas as Skills em ordem.

        Returns:
            Lista de SkillResult (uma por Skill executada com sucesso).

        Raises:
            RuntimeError: na primeira falha de Skill (após rollback).
        """
        log = logger.bind(agent=self.agent_name, run_id=context.run_id)
        log.info("agent_start", skills=[s.name for s in self.skills])

        results: list[SkillResult] = []
        executed: list[MCPSkill] = []

        for skill in self.skills:
            skill_log = log.bind(skill=skill.name, version=skill.version)
            skill_log.info("skill_start")
            t0 = time.monotonic()

            try:
                skill.validate(context)
                result = self._execute_with_retry(skill, context)

            except Exception as exc:
                duration_ms = int((time.monotonic() - t0) * 1000)
                skill_log.error(
                    "skill_failed",
                    error=str(exc),
                    duration_ms=duration_ms,
                )
                self._rollback_all(executed, context)
                raise RuntimeError(
                    f"[{self.agent_name}] Skill '{skill.name}' falhou: {exc}"
                ) from exc

            duration_ms = int((time.monotonic() - t0) * 1000)

            if not result.success:
                skill_log.error(
                    "skill_result_failed",
                    message=result.message,
                    duration_ms=duration_ms,
                )
                self._rollback_all(executed, context)
                raise RuntimeError(
                    f"[{self.agent_name}] Skill '{skill.name}' retornou falha: {result.message}"
                )

            skill_log.info(
                "skill_success",
                rows_affected=result.rows_affected,
                duration_ms=duration_ms,
            )
            results.append(result)
            executed.append(skill)

        log.info(
            "agent_done",
            skills_count=len(results),
            total_rows=sum(r.rows_affected for r in results),
        )
        return results

    # ── Retry ─────────────────────────────────────────────────────────────────

    def _execute_with_retry(
        self, skill: MCPSkill, context: ExecutionContext
    ) -> SkillResult:
        """
        Executa skill.execute() com retry e exponential backoff.

        Tenta max_retries vezes antes de desistir.
        Delay: 2^attempt segundos (2s, 4s, 8s, ...).
        """
        last_result: SkillResult | None = None
        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 2):  # +2: tentativas = max_retries + 1
            try:
                result = skill.execute(context)
                if result.success:
                    return result

                last_result = result
                if attempt <= self.max_retries:
                    wait = 2 ** attempt
                    logger.bind(
                        skill=skill.name,
                        run_id=context.run_id,
                        attempt=attempt,
                        wait_s=wait,
                    ).warning("skill_retry", message=result.message)
                    time.sleep(wait)

            except Exception as exc:
                last_exc = exc
                if attempt <= self.max_retries:
                    wait = 2 ** attempt
                    logger.bind(
                        skill=skill.name,
                        run_id=context.run_id,
                        attempt=attempt,
                        wait_s=wait,
                    ).warning("skill_retry_exception", error=str(exc))
                    time.sleep(wait)
                else:
                    raise

        if last_exc:
            raise last_exc

        # last_result nunca é None aqui (loop garantido pelo range)
        return last_result  # type: ignore[return-value]

    # ── Rollback ──────────────────────────────────────────────────────────────

    def _rollback_all(
        self, executed: list[MCPSkill], context: ExecutionContext
    ) -> None:
        """Aciona rollback em ordem reversa das Skills já executadas."""
        log = logger.bind(agent=self.agent_name, run_id=context.run_id)
        log.warning("agent_rollback_start", count=len(executed))

        for skill in reversed(executed):
            try:
                skill.rollback(context)
                log.info("skill_rollback_done", skill=skill.name)
            except Exception as exc:
                log.error("skill_rollback_failed", skill=skill.name, error=str(exc))

    def __repr__(self) -> str:
        return f"{self.agent_name}(skills={[s.name for s in self.skills]})"
