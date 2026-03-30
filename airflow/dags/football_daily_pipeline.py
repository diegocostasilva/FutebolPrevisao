"""
DAG: football_daily_pipeline

Orquestra o pipeline diário de dados de futebol:
  1. [ingestion]  FootballIngestionAgent  — API-Football → Bronze (Delta Lake)
  2. [processing] FootballProcessingAgent — Bronze → Silver (cluster Databricks)

Arquitetura:
    Airflow (WHEN/ORDER) → Agent.execute() → Skills → Databricks Jobs / API

Agendamento: 17:00 BRT (America/Sao_Paulo) todos os dias

Variáveis Airflow obrigatórias:
    DATABRICKS_HOST      — URL do workspace Databricks
    DATABRICKS_TOKEN     — PAT do Databricks (sensitive)
    API_FOOTBALL_KEY     — Chave da API-Football (sensitive)

Variáveis Airflow opcionais (têm defaults):
    ENVIRONMENT          — dev | staging | prod       (default: dev)
    LEAGUE_IDS           — IDs separados por vírgula  (default: 71)
    SEASON               — ano da temporada           (default: 2025)
    DATABRICKS_CLUSTER_ID — ID do cluster existente   (default: usa serverless)
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

# ── Defaults aplicados a todas as tasks ───────────────────────────────────────
_DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "email_on_failure": False,
    "email_on_retry": False,
    "sla": timedelta(hours=3),
}

# ── Helpers ───────────────────────────────────────────────────────────────────


def _build_context(dag_run, task_instance):
    """
    Constrói o ExecutionContext a partir do estado do DAG run.

    Credenciais vêm de Airflow Variables — nunca hardcoded.
    Parâmetros de execução vêm de Variables com defaults sensatos.
    O modo pode ser sobrescrito via dag_run.conf (ex: backfill manual).
    """
    import sys

    # Garante que src/ está disponível quando rodando dentro do container
    for path in ("/opt/airflow/project", "/opt/airflow"):
        if path not in sys.path:
            sys.path.insert(0, path)

    from src.core.context import ExecutionContext

    league_ids_raw = Variable.get("LEAGUE_IDS", default_var="71")
    league_ids = [int(x.strip()) for x in league_ids_raw.split(",") if x.strip()]

    override_mode = (dag_run.conf or {}).get("mode", "incremental")
    ingestion_date = (dag_run.conf or {}).get("ingestion_date", "")

    return ExecutionContext(
        run_id=dag_run.run_id,
        execution_date=dag_run.logical_date,
        dag_id=task_instance.dag_id,
        task_id=task_instance.task_id,
        environment=Variable.get("ENVIRONMENT", default_var="dev"),
        databricks_host=Variable.get("DATABRICKS_HOST"),
        databricks_token=Variable.get("DATABRICKS_TOKEN"),
        api_football_key=Variable.get("API_FOOTBALL_KEY"),
        params={
            "league_ids": league_ids,
            "season": int(Variable.get("SEASON", default_var="2025")),
            "mode": override_mode,
            "ingestion_date": ingestion_date,
            "databricks_cluster_id": Variable.get(
                "DATABRICKS_CLUSTER_ID", default_var=""
            ),
        },
    )


def _run_ingestion_agent(dag_run=None, task_instance=None, **kwargs):
    """
    Executa o FootballIngestionAgent: API-Football → Bronze Delta Lake.

    Persiste em XCom apenas métricas escalares (sem objetos pesados).
    """
    import sys

    for path in ("/opt/airflow/project", "/opt/airflow"):
        if path not in sys.path:
            sys.path.insert(0, path)

    from src.agents.football_ingestion_agent import FootballIngestionAgent

    context = _build_context(dag_run, task_instance)
    results = FootballIngestionAgent().execute(context)

    # Métricas para XCom (leves — apenas números e strings)
    metrics = {
        "skills_executed": len(results),
        "total_rows": sum(r.rows_affected for r in results),
        "fixture_ids_count": len(context.get_artifact("fixture_ids") or []),
        "ingestion_date": context.execution_date.date().isoformat(),
    }
    task_instance.xcom_push(key="ingestion_metrics", value=metrics)
    return metrics


def _run_processing_agent(dag_run=None, task_instance=None, **kwargs):
    """
    Executa o FootballProcessingAgent: Bronze → Silver via Databricks Jobs.

    Recupera ingestion_date da task de ingestão para filtrar apenas
    os dados do batch atual — evita reprocessar dados antigos.
    """
    import sys

    for path in ("/opt/airflow/project", "/opt/airflow"):
        if path not in sys.path:
            sys.path.insert(0, path)

    from src.agents.football_processing_agent import FootballProcessingAgent

    context = _build_context(dag_run, task_instance)

    # Pega ingestion_date do XCom da task de ingestão
    ingestion_metrics = task_instance.xcom_pull(
        task_ids="ingestion.run_ingestion_agent",
        key="ingestion_metrics",
    )
    if ingestion_metrics and ingestion_metrics.get("ingestion_date"):
        context.params["ingestion_date"] = ingestion_metrics["ingestion_date"]

    results = FootballProcessingAgent().execute(context)

    metrics = {
        "skills_executed": len(results),
        "total_rows": sum(r.rows_affected for r in results),
        "databricks_runs": [
            r.data.get("databricks_run_id")
            for r in results
            if r.data and r.data.get("databricks_run_id")
        ],
    }
    task_instance.xcom_push(key="processing_metrics", value=metrics)
    return metrics


# ── Callbacks de notificação ──────────────────────────────────────────────────


def _on_failure_callback(context):
    """
    Callback acionado quando qualquer task falha.

    Extensão futura: chamar NotificationAgent (Slack/PagerDuty).
    """
    import logging

    log = logging.getLogger("airflow.task")
    dag_id = context["dag"].dag_id
    task_id = context["task_instance"].task_id
    run_id = context["run_id"]
    exception = context.get("exception", "—")

    log.error(
        "[FAILURE] dag=%s task=%s run_id=%s error=%s",
        dag_id,
        task_id,
        run_id,
        exception,
    )


def _on_success_callback(context):
    """Callback de pipeline concluído com sucesso."""
    import logging

    log = logging.getLogger("airflow.task")
    dag_id = context["dag"].dag_id
    run_id = context["run_id"]
    log.info("[SUCCESS] dag=%s run_id=%s pipeline concluído.", dag_id, run_id)


# ── DAG ───────────────────────────────────────────────────────────────────────

with DAG(
    dag_id="football_daily_pipeline",
    description="Pipeline diário API-Football: ingestão Bronze + processamento Silver via Databricks",
    # 17:00 BRT — timezone America/Sao_Paulo configurado no airflow.cfg
    schedule="0 17 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=4),
    default_args=_DEFAULT_ARGS,
    tags=["football", "production", "daily"],
    on_failure_callback=_on_failure_callback,
    on_success_callback=_on_success_callback,
    doc_md="""
## football_daily_pipeline

Pipeline de dados de futebol executado diariamente às **17:00 BRT**.

### Fluxo
```
ingestion  →  processing
```

| Fase | Agent | Destino |
|------|-------|---------|
| ingestion | FootballIngestionAgent | Bronze Delta Lake |
| processing | FootballProcessingAgent | Silver Delta Lake (cluster Databricks) |

### Configuração manual (dag_run.conf)
```json
{
  "mode": "backfill",
  "ingestion_date": "2025-01-01"
}
```

### Variáveis Airflow requeridas
- `DATABRICKS_HOST`, `DATABRICKS_TOKEN`, `API_FOOTBALL_KEY`

### Variáveis Airflow opcionais
- `ENVIRONMENT`, `LEAGUE_IDS`, `SEASON`, `DATABRICKS_CLUSTER_ID`
""",
) as dag:

    with TaskGroup("ingestion", tooltip="API-Football → Bronze Delta Lake") as tg_ingestion:
        run_ingestion = PythonOperator(
            task_id="run_ingestion_agent",
            python_callable=_run_ingestion_agent,
            execution_timeout=timedelta(hours=2),
            doc_md="Executa FootballIngestionAgent: coleta dados da API-Football e persiste na Bronze.",
        )

    with TaskGroup("processing", tooltip="Bronze → Silver via Databricks Jobs") as tg_processing:
        run_processing = PythonOperator(
            task_id="run_processing_agent",
            python_callable=_run_processing_agent,
            execution_timeout=timedelta(hours=3),
            doc_md="Executa FootballProcessingAgent: dispara notebooks no cluster Databricks (Bronze→Silver).",
        )

    # Ordem: ingestão deve ser concluída antes do processamento
    tg_ingestion >> tg_processing
