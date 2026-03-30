# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MCP Agent DAG Platform** — a production data engineering platform built on a four-layer architecture:

```
Airflow (WHEN/ORDER) → Agents (HOW) → MCP Skills (WHAT) → Infrastructure (WHERE)
```

The architectural source of truth is `docs/PRD_ORIENTACAO_AGENTE_IA.md`. Consult it before any technical decision.

## Project Structure

```
├── airflow/              # Airflow runtime (DAGs, plugins, logs — mounted into containers)
│   ├── dags/
│   ├── plugins/
│   └── logs/
├── databricks/           # Databricks notebooks and jobs by medallion layer
│   ├── bronze/
│   ├── silver/
│   └── gold/
├── dbt/                  # dbt transformation project
│   ├── models/
│   │   ├── staging/      # views over Silver sources
│   │   ├── intermediate/ # ephemeral CTEs
│   │   └── mart/         # Delta tables for Gold layer
│   ├── tests/
│   │   ├── unit/
│   │   └── singular/
│   └── macros/
├── docs/                 # Architecture PRDs and reference docs
├── infra/                # Infrastructure configuration
│   ├── docker/           # Docker Compose files (4 separate stacks)
│   └── postgres/         # PostgreSQL init scripts
├── src/                  # Platform source code
│   ├── agents/           # Agent implementations (IngestionAgent, DBTAgent, etc.)
│   ├── skills/           # MCP Skill implementations
│   └── common/           # Shared: Context, SkillResult, BaseAgent
├── .env                  # Generated secrets (not committed)
├── requirements.txt      # Python dependencies
└── setup.sh              # Full stack bootstrap script
```

**Infrastructure commands** (all use `--project-directory` so paths resolve from project root):
```bash
# Start individual stacks
docker compose --project-directory . -f infra/docker/docker-compose.postgres.yml up -d
docker compose --project-directory . -f infra/docker/docker-compose.redis.yml up -d
docker compose --project-directory . -f infra/docker/docker-compose.airflow.yml up -d
docker compose --project-directory . -f infra/docker/docker-compose.spark.yml up -d

# Full stack from scratch
bash setup.sh
```

---

## Python Environment

- **Python 3.12** (mandatory — do not use 3.11 or earlier)
- venv at `/opt/mcp-platform/venv`
- Activate: `source /opt/mcp-platform/venv/bin/activate`
- All imports are direct — never use inline `pip install`

**Key dependencies by domain:**

| Domain | Packages |
|--------|----------|
| Core | pydantic, structlog, tenacity, python-dotenv, click |
| Data | psycopg2-binary, sqlalchemy, pandas, pyarrow |
| Databricks | databricks-sdk, databricks-sql-connector, pyspark, delta-spark |
| dbt | dbt-core, dbt-databricks, dbt-postgres |
| HTTP | requests, httpx |
| Testing | pytest, pytest-cov, pytest-mock |
| Quality | ruff, mypy, pre-commit |

**Commands:**
```bash
pytest                        # Run tests
ruff check . && ruff format . # Lint and format
mypy .                        # Type checking
pre-commit run --all-files    # All pre-commit hooks
```

---

## Architecture

### Non-Negotiable Principles

1. **Airflow never executes business logic** — DAGs call only Agents (via PythonOperator), except Databricks (DatabricksSubmitRunOperator).
2. **Skills are stateless** — receive Context, execute, return SkillResult. All needed state travels in Context.
3. **Context is the universal contract** — the only communication mechanism between layers.
4. **Fail-fast with rollback** — on Skill failure: stop execution, invoke rollback, propagate error.
5. **Data immutability by layer** — Bronze: append-only; Silver: MERGE upserts; Gold: idempotent overwrite/merge.

### Agent Taxonomy

| Agent | Responsibility | Skills Used |
|-------|---------------|-------------|
| IngestionAgent | Collect from sources → Bronze | API/JDBC/S3/CSV Extractor |
| ProcessingAgent | Bronze → Silver (clean, dedup, type) | SparkBronzeToSilver, SchemaEnforcer, RowCountCheck |
| DBTAgent | Run dbt staging → mart + tests | dbtRun, dbtTest, dbtDocs |
| ServingAgent | Load Gold → PostgreSQL serving | PGUpsert, PGLoader, CacheInvalidator |
| QualityAgent | Post-pipeline validation | RowCount, NullCheck, FreshnessCheck, SchemaDriftCheck |
| NotificationAgent | Alerts on success/failure/divergence | SlackNotifier, EmailNotifier, PagerDuty |

### MCP Skill Contract

Every Skill must implement:
- `name` — unique identifier using `domain_action` pattern (e.g., `spark_bronze_to_silver`, `postgres_upsert`)
- `version` — semantic version; breaking changes increment major
- `validate` — checks all preconditions before `execute`
- `execute(context) -> SkillResult` — main execution
- `rollback` — required if the Skill mutates data (INSERT/UPDATE/DELETE)

`SkillResult` fields: `success` (bool), `rows_affected` (int), `message` (str), `data` (dict, optional), `error` (exception, optional).

### DAG Requirements

Every DAG must have: `catchup=False`, `max_active_runs=1`, `execution_timeout`, `sla`, `retries`, `retry_delay`. Tags classify the DAG (e.g., `["mcp", "production", "daily"]`). Sensitive variables come from Airflow Variables or Connections — never hardcoded.

---

## Databricks / Delta Lake Rules

- **Format**: always Delta Lake — never raw Parquet, CSV, or JSON as managed tables
- **Catalog**: `mcp_platform` with schemas `bronze`, `silver`, `gold`
- **PARTITION BY**: only low-cardinality date columns (target 256 MB–1 GB per partition)
- **ZORDER BY**: high-cardinality columns used in point filters (max 4 columns); run via `OPTIMIZE`
- **Mandatory table properties**: `delta.autoOptimize.optimizeWrite = true`, `delta.autoOptimize.autoCompact = true`, tag `quality` = layer name
- **Mandatory load metadata columns**: `_loaded_at`, `_batch_id`, `_ingestion_date`
- **Maintenance schedule**: OPTIMIZE + ZORDER (weekly), VACUUM (weekly, min 168h Bronze/Silver, 720h Gold), ANALYZE after OPTIMIZE

### Layer Reference

| Layer | Purpose | Materialization | Retention |
|-------|---------|-----------------|-----------|
| Bronze | Raw data, schema-on-read | Append-only | 30 days |
| Silver | Cleaned, typed, deduplicated | MERGE upsert | 60 days |
| Gold | Aggregations and business marts | Overwrite/Merge (idempotent) | 90 days |

---

## dbt Rules

| dbt Layer | Materialization | Source | Purpose |
|-----------|----------------|--------|---------|
| staging | view | Silver sources | Rename, type, basic filters |
| intermediate | ephemeral | staging | Joins and enrichments (no physical table) |
| mart | table (Delta) | intermediate | Final aggregations for consumption |

- Staging reads from Silver sources only — never directly from Bronze
- Mart models require PARTITION BY and ZORDER via `post_hook`
- Every mart model needs schema tests (not_null, unique, accepted_values, range checks) in its YAML
- Unit tests for complex transformation logic using dbt 1.8+ native framework (`given`/`expect`)
- Singular tests for business rules that cross models
- `{% docs %}` block required for every mart model

```bash
dbt run            # Execute models
dbt test           # Run all tests (unit + schema + singular)
dbt docs generate  # Build lineage graph
dbt docs serve     # Serve docs at http://localhost:8001
```

---

## PostgreSQL Serving Layer

Two isolated instances:

| Instance | Port | Purpose |
|----------|------|---------|
| postgres-airflow | 5432 | Airflow metadata + Celery backend |
| postgres-serving | 5433 | Serving layer for BI, APIs, apps |

Schemas in `postgres-serving`:
- `serving` — consumption-ready data only
- `audit` — pipeline execution log (`audit.pipeline_execution` must be written by every load operation)
- `staging` — temporary area for incremental loads before upsert
- `cache` — materialized views for high-frequency dashboards

Rules: upsert via `INSERT ON CONFLICT` (never DELETE + INSERT), mandatory indexes on filter columns, PgBouncer for connection pooling in production.

---

## Infrastructure

All services connect via Docker bridge network `mcp_network` (created before any container starts).

| Service | Port | Default Credentials |
|---------|------|-------------------|
| PostgreSQL Airflow | 5432 | admin / admin |
| PostgreSQL Serving | 5433 | admin / admin |
| Redis | 6379 | — / admin |
| Airflow UI | 8080 | admin / admin |
| Celery Flower | 5555 | — |
| Spark UI | 8081 | — |
| dbt docs | 8001 | — |

**Credentials must be changed immediately after validating the stack is functional.**

Spark Standalone (local) mirrors Databricks behavior for development/testing only — production runs exclusively on Databricks.

---

## Observability

- **Logging**: structlog, structured JSON, every Skill logs start/end with duration (ms) and rows processed; `run_id` and `execution_date` in every log line
- **Metrics**: Prometheus + Grafana (duration, rows, error rate)
- **Alerts**: Notification Agent → Slack / PagerDuty
- **Audit**: `audit.pipeline_execution` in PostgreSQL (run_id, agent, skill, status, rows_affected, duration)
- **Lineage**: `dbt docs` + OpenLineage
