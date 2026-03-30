"""
DatabricksJobBaseSkill — base para Skills que executam notebooks/jobs no Databricks.

Arquitetura correta:
    Airflow (WHEN) → Skill (WHAT) → Databricks Jobs API → Cluster Spark → Delta Lake

A Skill NÃO executa Spark localmente. Ela:
  1. Submete um notebook run via Databricks Jobs SDK
  2. Aguarda conclusão (polling)
  3. Retorna SkillResult com status e métricas do job

Isso garante que todo processamento ocorra no cluster Databricks,
usando o Spark e Delta Lake nativos do ambiente.
"""

from __future__ import annotations

import time
from typing import Any

import structlog
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import (
    NotebookTask,
    RunLifeCycleState,
    RunResultState,
    SubmitTask,
)

from src.core.context import ExecutionContext
from src.core.exceptions import MCPExecutionError, MCPValidationError
from src.core.result import SkillResult
from src.core.skill_base import MCPSkill

logger = structlog.get_logger(__name__)

# Polling a cada 15s; timeout padrão de 2h
_POLL_INTERVAL_S = 15
_DEFAULT_TIMEOUT_S = 7200


class DatabricksJobBaseSkill(MCPSkill):
    """
    Base para Skills que executam processamento no cluster Databricks.

    Subclasses devem implementar:
        - name, version
        - notebook_path → caminho do notebook no workspace Databricks
        - validate(context)
        - _build_notebook_params(context) → dict de parâmetros para o notebook

    Opcionalmente:
        - cluster_id_param → nome do param no context.params que contém o cluster_id
        - timeout_s → timeout em segundos (padrão 2h)
    """

    # Notebook a executar — definido pela subclasse
    @property
    def notebook_path(self) -> str:
        raise NotImplementedError

    @property
    def timeout_s(self) -> int:
        return _DEFAULT_TIMEOUT_S

    # ── Validação compartilhada ───────────────────────────────────────────────

    def validate(self, context: ExecutionContext) -> bool:
        if not context.databricks_host:
            raise MCPValidationError(
                "databricks_host não definido no contexto",
                skill_name=self.name,
            )
        if not context.databricks_token:
            raise MCPValidationError(
                "databricks_token não definido no contexto",
                skill_name=self.name,
            )
        return True

    # ── Execução via Jobs SDK ─────────────────────────────────────────────────

    def _run_notebook(
        self,
        context: ExecutionContext,
        extra_params: dict[str, Any] | None = None,
    ) -> SkillResult:
        """
        Submete o notebook como one-time run e aguarda conclusão.

        Args:
            context:      ExecutionContext com credenciais Databricks.
            extra_params: Parâmetros adicionais para o notebook.

        Returns:
            SkillResult com métricas do job (output, duração, rows).
        """
        log = logger.bind(skill=self.name, run_id=context.run_id)

        params = self._build_notebook_params(context)
        if extra_params:
            params.update(extra_params)

        # Sempre passa run_id e execution_date para rastreabilidade
        params["run_id"] = context.run_id
        params["execution_date"] = context.execution_date.isoformat()
        params["catalog"] = "football_prediction"

        ws = WorkspaceClient(
            host=context.databricks_host,
            token=context.databricks_token,
        )

        log.info(
            "databricks_job_submit",
            notebook=self.notebook_path,
            params=params,
        )

        # Determina cluster: usa existing cluster se disponível, senão serverless
        cluster_id = context.params.get("databricks_cluster_id") or ""
        notebook_task = NotebookTask(
            notebook_path=self.notebook_path,
            base_parameters=params,
        )
        task = SubmitTask(
            task_key=self.name,
            notebook_task=notebook_task,
            existing_cluster_id=cluster_id if cluster_id else None,
        )

        try:
            run = ws.jobs.submit(
                run_name=f"{self.name}_{context.run_id[:8]}",
                tasks=[task],
            )
            run_id = run.run_id
            log.info("databricks_job_submitted", run_id=run_id)

        except Exception as exc:
            raise MCPExecutionError(
                f"Falha ao submeter job Databricks: {exc}",
                skill_name=self.name,
            ) from exc

        # Polling até conclusão
        return self._wait_for_run(ws, run_id, context, log)

    def _wait_for_run(
        self,
        ws: WorkspaceClient,
        run_id: int,
        context: ExecutionContext,
        log: Any,
    ) -> SkillResult:
        """Aguarda o job terminar via polling e retorna SkillResult."""
        elapsed = 0

        while elapsed < self.timeout_s:
            run = ws.jobs.get_run(run_id=run_id)
            state = run.state

            life = state.life_cycle_state
            result = state.result_state

            log.debug(
                "databricks_job_polling",
                run_id=run_id,
                life_cycle=life,
                elapsed_s=elapsed,
            )

            if life in (
                RunLifeCycleState.TERMINATED,
                RunLifeCycleState.SKIPPED,
                RunLifeCycleState.INTERNAL_ERROR,
            ):
                duration_ms = int(elapsed * 1000)

                if result == RunResultState.SUCCESS:
                    # Tenta extrair rows_affected do output do notebook
                    rows = self._extract_rows_from_output(ws, run_id)
                    log.info(
                        "databricks_job_success",
                        run_id=run_id,
                        rows=rows,
                        duration_ms=duration_ms,
                    )
                    return SkillResult.ok(
                        f"Job Databricks concluído com sucesso: {self.notebook_path}",
                        rows_affected=rows,
                        data={"databricks_run_id": run_id, "duration_ms": duration_ms},
                    )
                else:
                    error_msg = state.state_message or "Sem mensagem de erro"
                    log.error(
                        "databricks_job_failed",
                        run_id=run_id,
                        result=result,
                        message=error_msg,
                    )
                    return SkillResult(
                        success=False,
                        message=f"Job Databricks falhou ({result}): {error_msg}",
                        data={"databricks_run_id": run_id},
                    )

            time.sleep(_POLL_INTERVAL_S)
            elapsed += _POLL_INTERVAL_S

        return SkillResult(
            success=False,
            message=f"Job Databricks timeout após {self.timeout_s}s (run_id={run_id})",
            data={"databricks_run_id": run_id},
        )

    def _extract_rows_from_output(self, ws: WorkspaceClient, run_id: int) -> int:
        """
        Tenta extrair rows_affected do output do notebook.

        Convenção: o notebook deve exibir um JSON no último cell com:
            {"rows_affected": 123}
        """
        try:
            output = ws.jobs.get_run_output(run_id=run_id)
            if output.notebook_output and output.notebook_output.result:
                import json
                data = json.loads(output.notebook_output.result)
                return int(data.get("rows_affected", 0))
        except Exception:
            pass
        return 0

    def _build_notebook_params(self, context: ExecutionContext) -> dict[str, Any]:
        """
        Constrói os parâmetros base para o notebook.
        Subclasses podem sobrescrever para adicionar params específicos.
        """
        return {
            "league_ids": ",".join(str(x) for x in context.league_ids),
            "season": str(context.season),
            "mode": context.mode,
        }
