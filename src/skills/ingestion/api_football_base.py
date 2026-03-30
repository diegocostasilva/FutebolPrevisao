"""
APIFootballBaseSkill — classe base para todas as Skills que consomem a API-Football v3.

Responsabilidades compartilhadas:
  - Autenticação via header x-apisports-key
  - Rate limiting (sleep entre chamadas)
  - Retry com exponential backoff (tenacity)
  - Verificação de quota da API
  - Escrita de JSON bruto na camada Bronze (Delta Lake)
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, date, datetime
from typing import Any

import requests
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.core.context import ExecutionContext
from src.core.exceptions import MCPExecutionError, MCPQuotaExceededError, MCPValidationError
from src.core.result import SkillResult
from src.core.skill_base import MCPSkill

logger = structlog.get_logger(__name__)

_BASE_URL = "https://v3.football.api-sports.io"
_REQUESTS_PER_MINUTE = 30  # plano free: 30 req/min
_SLEEP_BETWEEN_CALLS = 60 / _REQUESTS_PER_MINUTE  # 2s por chamada


class _QuotaExhausted(Exception):
    """Sinaliza quota esgotada para o mecanismo de retry ignorar."""


class APIFootballBaseSkill(MCPSkill):
    """
    Base para Skills de ingestão da API-Football.

    Subclasses devem implementar:
        - name, version
        - validate(context)  ← chamar super().validate(context) primeiro
        - execute(context)   ← usar _make_request + _write_to_bronze
    """

    # ── Validação compartilhada ───────────────────────────────────────────────

    def validate(self, context: ExecutionContext) -> bool:
        if not context.api_football_key:
            raise MCPValidationError(
                "api_football_key não definida no contexto",
                skill_name=self.name,
            )
        return True

    # ── HTTP ──────────────────────────────────────────────────────────────────

    @retry(
        retry=retry_if_exception_type((requests.HTTPError, requests.Timeout)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def _make_request(
        self,
        endpoint: str,
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> tuple[list[dict[str, Any]], dict[str, str]]:
        """
        Faz GET para o endpoint informado.

        Returns:
            (response_list, response_headers)

        Raises:
            MCPQuotaExceededError: se quota esgotada.
            MCPExecutionError: em falha HTTP irrecuperável.
        """
        url = f"{_BASE_URL}/{endpoint.lstrip('/')}"
        headers = {"x-apisports-key": context.api_football_key}

        log = logger.bind(
            skill=self.name,
            run_id=context.run_id,
            endpoint=endpoint,
            params=params,
        )
        log.debug("api_request_start")

        response = requests.get(url, headers=headers, params=params, timeout=30)

        # Rate-limit explícito (429) → retry via tenacity
        if response.status_code == 429:
            log.warning("api_rate_limited", status=429)
            response.raise_for_status()

        if response.status_code >= 500:
            log.error("api_server_error", status=response.status_code)
            response.raise_for_status()

        if not response.ok:
            raise MCPExecutionError(
                f"API retornou {response.status_code} para {endpoint}",
                skill_name=self.name,
            )

        payload = response.json()
        self._check_quota(response.headers, context)

        results: list[dict[str, Any]] = payload.get("response", [])
        log.debug("api_request_done", count=len(results))

        # Respeitar rate limit
        time.sleep(_SLEEP_BETWEEN_CALLS)

        return results, dict(response.headers)

    # ── Quota ─────────────────────────────────────────────────────────────────

    def _check_quota(self, headers: Any, context: ExecutionContext) -> None:
        """
        Verifica cabeçalhos de quota.
        - > 80% consumido → warning
        - = 0 restantes → MCPQuotaExceededError
        """
        try:
            remaining = int(headers.get("x-ratelimit-requests-remaining", 1))
            limit = int(headers.get("x-ratelimit-requests-limit", 100))
        except (ValueError, TypeError):
            return

        context.set_artifact("quota_remaining", remaining)
        context.set_artifact("quota_limit", limit)

        consumed_pct = ((limit - remaining) / limit * 100) if limit else 0

        log = logger.bind(skill=self.name, run_id=context.run_id)

        if remaining == 0:
            log.error("api_quota_exhausted", remaining=remaining, limit=limit)
            raise MCPQuotaExceededError(
                f"Quota da API-Football esgotada ({limit} requests/dia)",
                remaining=remaining,
                limit=limit,
            )

        if consumed_pct >= 95:
            log.error("api_quota_critical", pct=consumed_pct, remaining=remaining)
            context.set_artifact("quota_critical", True)
        elif consumed_pct >= 80:
            log.warning("api_quota_high", pct=consumed_pct, remaining=remaining)

    # ── Bronze write ──────────────────────────────────────────────────────────

    def _write_to_bronze(
        self,
        records: list[dict[str, Any]],
        table_name: str,
        endpoint: str,
        context: ExecutionContext,
    ) -> int:
        """
        Persiste records como JSON bruto em tabela Delta Bronze.

        Estratégia de escrita:
          1. SparkSession disponível no contexto → saveAsTable (testes/Databricks Connect)
          2. Sem SparkSession → INSERT via Databricks SQL Connector (produção/Airflow)

        Adiciona metadados obrigatórios: _ingestion_date, _ingestion_ts,
        _batch_id, _source_endpoint.
        """
        if not records:
            return 0

        import json

        batch_id = str(uuid.uuid4())
        ingestion_date = date.today().isoformat()
        ingestion_ts = datetime.now(UTC).isoformat()
        full_table = f"football_prediction.bronze.{table_name}"

        rows = [
            (
                json.dumps(record),
                endpoint,
                ingestion_date,
                ingestion_ts,
                batch_id,
                endpoint,
            )
            for record in records
        ]

        log = logger.bind(skill=self.name, run_id=context.run_id)

        spark = context.spark_session
        if spark is not None:
            # Caminho Spark (testes ou Databricks Connect)
            from pyspark.sql import Row
            df = spark.createDataFrame(
                [Row(payload=r[0], endpoint=r[1], _ingestion_date=r[2],
                     _ingestion_ts=r[3], _batch_id=r[4], _source_endpoint=r[5])
                 for r in rows]
            )
            df.write.format("delta").mode("append").saveAsTable(full_table)
        else:
            # Caminho produção: INSERT via SQL Warehouse (sem cluster Spark)
            if not context.databricks_host or not context.databricks_token:
                raise MCPExecutionError(
                    "databricks_host/token ausentes — não é possível gravar na Bronze",
                    skill_name=self.name,
                )
            http_path = (
                context.databricks_http_path
                or f"/sql/1.0/warehouses/a15a748006670d03"
            )
            from databricks import sql as dbsql

            insert_sql = (
                f"INSERT INTO {full_table} "
                "(payload, endpoint, _ingestion_date, _ingestion_ts, _batch_id, _source_endpoint) "
                "VALUES (?, ?, ?, ?, ?, ?)"
            )
            host = context.databricks_host.replace("https://", "").rstrip("/")
            with dbsql.connect(
                server_hostname=host,
                http_path=http_path,
                access_token=context.databricks_token,
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(insert_sql, rows)

        log.info("bronze_write_done", table=table_name, rows=len(rows), batch_id=batch_id)
        return len(rows)
