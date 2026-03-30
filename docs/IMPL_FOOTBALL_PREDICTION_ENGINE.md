# Guia de Implementação — Football Prediction Engine

## Mapa Completo de Código e Localização

| Campo              | Valor                                                          |
|--------------------|----------------------------------------------------------------|
| Versão             | 1.0.0                                                          |
| Data               | 2026-03-29                                                     |
| Base               | PRD_FOOTBALL_PREDICTION_ENGINE.md                              |
| Infraestrutura     | INFRA_MCP_AGENT_DAG_PLATFORM.md                                |
| Princípios         | PRD_ORIENTACAO_AGENTE_IA.md                                    |
| Total de Arquivos  | 147 arquivos em 42 diretórios                                  |

---

## 1. Árvore Completa do Projeto

```
football-prediction-engine/
│
├── .env.example
├── .env
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml
├── Makefile
├── README.md
│
├── docker/
│   ├── docker-compose.yml                          ← Master compose
│   ├── postgres/
│   │   ├── docker-compose.postgres.yml
│   │   └── init/
│   │       ├── 01_create_databases.sql
│   │       ├── 02_create_schemas.sql
│   │       ├── 03_create_roles.sql
│   │       └── 04_football_serving_tables.sql
│   ├── redis/
│   │   └── docker-compose.redis.yml
│   ├── airflow/
│   │   ├── docker-compose.airflow.yml
│   │   ├── Dockerfile.airflow
│   │   └── requirements-airflow.txt
│   ├── spark/
│   │   └── docker-compose.spark.yml
│   ├── mlflow/
│   │   ├── docker-compose.mlflow.yml
│   │   └── Dockerfile.mlflow
│   └── api/
│       ├── docker-compose.api.yml
│       └── Dockerfile.api
│
├── mcp/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── context.py
│   │   ├── skill_base.py
│   │   ├── skill_registry.py
│   │   ├── result.py
│   │   └── exceptions.py
│   └── skills/
│       ├── __init__.py
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── api_football_base.py
│       │   ├── api_football_leagues.py
│       │   ├── api_football_fixtures.py
│       │   ├── api_football_statistics.py
│       │   ├── api_football_events.py
│       │   ├── api_football_lineups.py
│       │   ├── api_football_players.py
│       │   ├── api_football_odds.py
│       │   ├── api_football_standings.py
│       │   ├── api_football_injuries.py
│       │   ├── api_football_predictions.py
│       │   ├── api_football_teams.py
│       │   └── api_football_quota_monitor.py
│       ├── processing/
│       │   ├── __init__.py
│       │   ├── spark_football_fixtures_flatten.py
│       │   ├── spark_football_statistics_flatten.py
│       │   ├── spark_football_events_normalize.py
│       │   ├── spark_football_odds_normalize.py
│       │   ├── spark_football_dedup.py
│       │   └── spark_football_key_generator.py
│       ├── dbt/
│       │   ├── __init__.py
│       │   ├── dbt_football_run.py
│       │   ├── dbt_football_test.py
│       │   └── dbt_football_docs.py
│       ├── ml/
│       │   ├── __init__.py
│       │   ├── ml_feature_store_loader.py
│       │   ├── ml_model_training.py
│       │   ├── ml_model_evaluation.py
│       │   ├── ml_model_registry.py
│       │   ├── ml_prediction_generator.py
│       │   └── ml_prediction_writer.py
│       ├── serving/
│       │   ├── __init__.py
│       │   ├── postgres_predictions_upsert.py
│       │   ├── postgres_standings_upsert.py
│       │   ├── postgres_team_form_upsert.py
│       │   ├── postgres_fixtures_upsert.py
│       │   └── cache_invalidator.py
│       ├── quality/
│       │   ├── __init__.py
│       │   ├── quality_fixture_count_check.py
│       │   ├── quality_odds_range_check.py
│       │   ├── quality_prediction_sum_check.py
│       │   ├── quality_freshness_check.py
│       │   └── quality_model_drift_check.py
│       └── notification/
│           ├── __init__.py
│           ├── slack_notifier.py
│           └── email_notifier.py
│
├── agents/
│   ├── __init__.py
│   ├── base_agent.py
│   ├── football_ingestion_agent.py
│   ├── football_processing_agent.py
│   ├── football_dbt_agent.py
│   ├── football_ml_agent.py
│   ├── football_serving_agent.py
│   ├── football_quality_agent.py
│   └── football_notification_agent.py
│
├── airflow/
│   ├── dags/
│   │   ├── football_daily_pipeline.py
│   │   ├── football_matchday_pipeline.py
│   │   ├── football_weekly_retrain.py
│   │   ├── football_weekly_maintenance.py
│   │   └── football_season_init.py
│   └── plugins/
│       └── mcp_airflow_plugin.py
│
├── databricks/
│   ├── schemas/
│   │   ├── 01_create_catalog.sql
│   │   ├── 02_bronze_ddl.sql
│   │   ├── 03_silver_ddl.sql
│   │   └── 04_gold_ddl.sql
│   ├── notebooks/
│   │   ├── bronze/
│   │   │   └── ingest_api_football_to_bronze.py
│   │   ├── silver/
│   │   │   ├── bronze_to_silver_fixtures.py
│   │   │   ├── bronze_to_silver_statistics.py
│   │   │   ├── bronze_to_silver_events.py
│   │   │   ├── bronze_to_silver_odds.py
│   │   │   └── bronze_to_silver_standings.py
│   │   └── gold/
│   │       └── generate_predictions_output.py
│   ├── jobs/
│   │   ├── daily_bronze_ingestion.py
│   │   └── daily_silver_processing.py
│   └── maintenance/
│       ├── optimize_football_tables.py
│       └── vacuum_football_tables.py
│
├── dbt_project/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── packages.yml
│   ├── models/
│   │   ├── staging/
│   │   │   └── football/
│   │   │       ├── _football_sources.yml
│   │   │       ├── _football_staging_schema.yml
│   │   │       ├── stg_football_fixtures.sql
│   │   │       ├── stg_football_match_statistics.sql
│   │   │       ├── stg_football_match_events.sql
│   │   │       ├── stg_football_odds_prematch.sql
│   │   │       ├── stg_football_standings.sql
│   │   │       ├── stg_football_injuries.sql
│   │   │       ├── stg_football_players.sql
│   │   │       └── stg_football_api_predictions.sql
│   │   ├── intermediate/
│   │   │   └── football/
│   │   │       ├── int_football_team_form.sql
│   │   │       ├── int_football_elo_ratings.sql
│   │   │       ├── int_football_head_to_head.sql
│   │   │       ├── int_football_odds_consensus.sql
│   │   │       ├── int_football_player_impact.sql
│   │   │       └── int_football_match_context.sql
│   │   └── mart/
│   │       └── football/
│   │           ├── _football_mart_schema.yml
│   │           ├── _football_mart_docs.md
│   │           ├── fct_match_features.sql
│   │           ├── fct_team_form.sql
│   │           ├── fct_team_strength.sql
│   │           ├── fct_head_to_head.sql
│   │           ├── fct_player_impact.sql
│   │           ├── fct_odds_consensus.sql
│   │           ├── fct_match_predictions.sql
│   │           ├── fct_model_performance.sql
│   │           ├── fct_league_summary.sql
│   │           ├── fct_team_season_stats.sql
│   │           ├── dim_teams.sql
│   │           ├── dim_leagues.sql
│   │           └── dim_players.sql
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_fct_team_form.yml
│   │   │   ├── test_fct_match_features.yml
│   │   │   ├── test_fct_team_strength.yml
│   │   │   └── test_fct_odds_consensus.yml
│   │   └── singular/
│   │       ├── assert_no_future_features.sql
│   │       ├── assert_prediction_probabilities_sum.sql
│   │       ├── assert_elo_rating_reasonable.sql
│   │       ├── assert_no_orphan_statistics.sql
│   │       └── assert_complete_rounds.sql
│   ├── macros/
│   │   ├── generate_surrogate_key.sql
│   │   ├── calculate_elo.sql
│   │   ├── calculate_form.sql
│   │   └── optimize_delta.sql
│   ├── snapshots/
│   │   ├── snap_standings.sql
│   │   └── snap_team_strength.sql
│   └── seeds/
│       ├── league_metadata.csv
│       └── team_aliases.csv
│
├── api/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── predictions.py
│   │   ├── fixtures.py
│   │   ├── standings.py
│   │   ├── teams.py
│   │   └── model_metrics.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── prediction.py
│   │   ├── fixture.py
│   │   ├── standing.py
│   │   ├── team.py
│   │   └── model.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── prediction_service.py
│   │   ├── fixture_service.py
│   │   └── standing_service.py
│   └── database/
│       ├── __init__.py
│       └── connection.py
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_skills/
│   │   │   ├── test_api_football_base.py
│   │   │   ├── test_api_football_fixtures.py
│   │   │   ├── test_spark_fixtures_flatten.py
│   │   │   ├── test_ml_model_training.py
│   │   │   ├── test_postgres_upsert.py
│   │   │   └── test_quality_checks.py
│   │   ├── test_agents/
│   │   │   ├── test_ingestion_agent.py
│   │   │   ├── test_processing_agent.py
│   │   │   ├── test_ml_agent.py
│   │   │   └── test_serving_agent.py
│   │   └── test_api/
│   │       ├── test_predictions_router.py
│   │       └── test_fixtures_router.py
│   └── integration/
│       ├── test_pipeline_e2e.py
│       └── test_api_football_connection.py
│
├── scripts/
│   ├── setup_venv.sh
│   ├── start_all.sh
│   ├── stop_all.sh
│   ├── health_check.sh
│   ├── init_databricks_schemas.sh
│   ├── backfill_season.py
│   └── seed_league_config.py
│
├── config/
│   ├── leagues.yml
│   ├── endpoints.yml
│   └── model_config.yml
│
└── docs/
    ├── architecture.md
    ├── runbook.md
    ├── data_dictionary.md
    ├── api_reference.md
    └── adr/
        ├── 001_medallion_architecture.md
        ├── 002_agent_pattern.md
        ├── 003_elo_rating_system.md
        ├── 004_stacking_ensemble.md
        └── 005_api_football_quota_management.md
```

---

## 2. Camada de Infraestrutura — Docker

Cada ferramenta opera em seu próprio Docker Compose, conectada via `mcp_network`.

---

### 2.1 `docker/docker-compose.yml`

**Localização**: `docker/docker-compose.yml`
**Propósito**: Master compose que orquestra todos os serviços via `include`.

**Especificação**:
- Importa todos os docker-compose individuais via diretiva `include`.
- Declara `mcp_network` como rede external.
- Não define serviços próprios — apenas agrega.

**Dependências**: Todos os docker-compose filhos.

---

### 2.2 `docker/postgres/docker-compose.postgres.yml`

**Localização**: `docker/postgres/`
**Propósito**: Duas instâncias PostgreSQL isoladas.

**Serviços**:

| Serviço           | Container                | Porta | Banco       | Função                     |
|-------------------|--------------------------|-------|-------------|----------------------------|
| postgres-airflow  | mcp_postgres_airflow     | 5432  | airflow_db  | Metadata Airflow + Celery  |
| postgres-serving  | mcp_postgres_serving     | 5433  | serving_db  | Serving layer + audit      |

**Especificação**:
- Imagem: `postgres:16-alpine`.
- Credenciais: `admin / admin` (trocar após deploy).
- Healthcheck: `pg_isready` a cada 10s.
- Volumes nomeados para persistência.
- Scripts de init em `docker-entrypoint-initdb.d/`.
- Rede: `mcp_network` (external).
- Limites: 1G RAM para airflow, 2G RAM para serving.

---

### 2.3 `docker/postgres/init/01_create_databases.sql`

**Propósito**: Criar database auxiliar e extensões.

**Implementar**:
- `CREATE EXTENSION pg_stat_statements`.
- `CREATE EXTENSION pgcrypto`.
- `CREATE DATABASE mcp_metadata`.

---

### 2.4 `docker/postgres/init/02_create_schemas.sql`

**Propósito**: Criar schemas do serving layer e tabela de auditoria.

**Implementar**:
- Schemas: `staging`, `serving`, `audit`, `cache`.
- Tabela `audit.pipeline_execution` com campos: execution_id, run_id, dag_id, agent_name, skill_name, skill_version, status, rows_affected, error_message, started_at, finished_at, duration_ms (computed).
- Índices em run_id, dag_id, status.

---

### 2.5 `docker/postgres/init/03_create_roles.sql`

**Propósito**: Roles de acesso (reader para BI, writer para pipeline).

**Implementar**:
- `role_reader`: SELECT em serving.
- `role_writer`: ALL em serving, staging, audit.
- Credenciais `admin / admin`.

---

### 2.6 `docker/postgres/init/04_football_serving_tables.sql`

**Propósito**: Tabelas do domínio Football no serving layer.

**Tabelas a criar**:

| Tabela                              | PK                    | Índices Adicionais                    |
|-------------------------------------|-----------------------|---------------------------------------|
| serving.match_predictions           | fixture_id            | match_date DESC, league_id            |
| serving.upcoming_fixtures           | fixture_id            | match_date, league_id                 |
| serving.league_standings            | league_id + team_id + season | league_id, position             |
| serving.team_form                   | team_id + season      | team_id                               |
| serving.model_metrics               | model_version         | created_at DESC                       |
| serving.historical_predictions      | id (serial)           | fixture_id, model_version, match_date |

**Campos de `serving.match_predictions`**:
- fixture_id (INT PK), league_id, league_name, season, match_date, home_team_id, home_team_name, away_team_id, away_team_name, prob_home_win (NUMERIC 5,4), prob_draw (NUMERIC 5,4), prob_away_win (NUMERIC 5,4), confidence (VARCHAR 10), model_version, home_form (VARCHAR 10), away_form (VARCHAR 10), home_elo (INT), away_elo (INT), odd_home (NUMERIC 6,2), odd_draw (NUMERIC 6,2), odd_away (NUMERIC 6,2), generated_at (TIMESTAMP), _loaded_at (TIMESTAMP DEFAULT NOW).

**Campos de `serving.upcoming_fixtures`**:
- fixture_id (INT PK), league_id, league_name, season, round, match_date, match_time, venue, home_team_id, home_team_name, home_team_logo, away_team_id, away_team_name, away_team_logo, status, has_prediction (BOOLEAN), _loaded_at.

**Campos de `serving.league_standings`**:
- league_id, team_id, season (PK composta), position, team_name, played, wins, draws, losses, goals_for, goals_against, goal_diff, points, form (VARCHAR 10), _loaded_at.

**Campos de `serving.team_form`**:
- team_id, season (PK composta), team_name, wins_last_5, draws_last_5, losses_last_5, goals_scored_avg_5, goals_conceded_avg_5, points_last_5, form_string (VARCHAR 10), elo_rating, _loaded_at.

**Campos de `serving.model_metrics`**:
- model_version (VARCHAR PK), model_type, log_loss, accuracy, brier_score, roc_auc, total_predictions, correct_predictions, training_samples, feature_count, trained_at, promoted_at, is_active (BOOLEAN).

**Campos de `serving.historical_predictions`**:
- id (SERIAL PK), fixture_id, match_date, prob_home_win, prob_draw, prob_away_win, predicted_result (H/D/A), actual_result (H/D/A NULL), was_correct (BOOLEAN NULL), model_version, generated_at, result_updated_at.

**Materialized Views a criar**:
- `serving.mv_round_predictions`: predições agrupadas por rodada/liga.
- `serving.mv_model_accuracy_trend`: acurácia acumulada por mês.

---

### 2.7 `docker/redis/docker-compose.redis.yml`

**Localização**: `docker/redis/`
**Propósito**: Broker Celery do Airflow.

**Especificação**:
- Imagem: `redis:7-alpine`.
- Senha: `admin`.
- maxmemory: 512MB, policy allkeys-lru.
- AOF habilitado.
- Porta: 6379.

---

### 2.8 `docker/airflow/docker-compose.airflow.yml`

**Localização**: `docker/airflow/`
**Propósito**: Airflow completo com CeleryExecutor.

**Serviços**: airflow-init, airflow-webserver (:8080), airflow-scheduler, airflow-worker (concurrency 4), airflow-flower (:5555).

**Especificação do Dockerfile.airflow**:
- Base: `apache/airflow:2.9.3-python3.12`.
- Instalar: providers-databricks, providers-postgres, providers-redis, providers-slack, providers-celery.
- Instalar: psycopg2-binary, sqlalchemy, requests, pydantic, tenacity, structlog, databricks-sdk, scikit-learn, xgboost, lightgbm, mlflow-skinny.
- Volumes montados: dags, agents, mcp, dbt_project, config.
- Timezone: `America/Sao_Paulo`.
- airflow-init: `db migrate` + criar user admin/admin + registrar connections (postgres_serving, databricks_default).

---

### 2.9 `docker/spark/docker-compose.spark.yml`

**Localização**: `docker/spark/`
**Propósito**: Spark standalone para desenvolvimento local.

**Serviços**: spark-master (:8081, :7077), spark-worker-1.
- Imagem: `bitnami/spark:3.5.1`.
- Worker: 4G RAM, 2 cores.

---

### 2.10 `docker/mlflow/docker-compose.mlflow.yml`

**Localização**: `docker/mlflow/`
**Propósito**: MLflow Tracking Server para registro de modelos.

**Especificação**:
- Imagem custom baseada em `python:3.12-slim`.
- Backend store: `postgresql://admin:admin@postgres-serving:5432/serving_db`.
- Artifact store: `/mlflow/artifacts` (volume local) ou S3 (produção).
- Porta: 5000.
- UI: `http://localhost:5000`.

---

### 2.11 `docker/api/docker-compose.api.yml`

**Localização**: `docker/api/`
**Propósito**: FastAPI de predições.

**Especificação**:
- Imagem custom baseada em `python:3.12-slim`.
- Instalar: fastapi, uvicorn, psycopg2-binary, pydantic, httpx.
- Porta: 8000.
- Variáveis: PG_SERVING_HOST, PG_SERVING_PORT, PG_SERVING_DB, PG_SERVING_USER, PG_SERVING_PASSWORD.
- Health: `/health`.

---

## 3. Camada MCP Core

Estes arquivos definem o framework base. Todos os outros componentes dependem deles.

---

### 3.1 `mcp/core/context.py`

**Propósito**: Objeto ExecutionContext compartilhado entre Skills e Agents.

**Implementar**:
- Dataclass com campos: run_id (str), execution_date (datetime), dag_id (str), task_id (str), environment (str — dev/staging/prod).
- Campos de conexão: spark_session (Any), pg_connection (Any), databricks_token (str), databricks_host (str), api_football_key (str).
- Campos dinâmicos: params (dict), artifacts (dict).
- Property `is_production` → True se environment == "prod".
- Property `league_ids` → retorna lista de IDs de ligas do params ou default [71].

---

### 3.2 `mcp/core/skill_base.py`

**Propósito**: Classe abstrata base para todas as Skills.

**Implementar**:
- Classe abstrata `MCPSkill` com:
  - Property abstrata `name` → str.
  - Property abstrata `version` → str.
  - Método abstrato `validate(context) → bool` (levanta exceção se inválido).
  - Método abstrato `execute(context) → SkillResult`.
  - Método opcional `rollback(context) → None`.

---

### 3.3 `mcp/core/result.py`

**Propósito**: Objeto padronizado de retorno de toda Skill.

**Implementar**:
- Dataclass `SkillResult` com: success (bool), rows_affected (int default 0), message (str), data (dict optional), error (Exception optional).

---

### 3.4 `mcp/core/skill_registry.py`

**Propósito**: Registro centralizado de Skills disponíveis.

**Implementar**:
- Classe `SkillRegistry` com dict interno `_skills`.
- Métodos: `register(skill)`, `get(name) → MCPSkill`, `list_all() → list[str]`.
- Decorator `@register_skill` para auto-registro.

---

### 3.5 `mcp/core/exceptions.py`

**Propósito**: Exceções customizadas da plataforma.

**Implementar**:
- `MCPSkillError(Exception)` — erro genérico de Skill.
- `MCPValidationError(MCPSkillError)` — falha na validação.
- `MCPExecutionError(MCPSkillError)` — falha na execução.
- `MCPQuotaExceededError(MCPSkillError)` — quota da API esgotada.
- `MCPDataLeakageError(MCPSkillError)` — feature usando dados futuros.

---

## 4. Camada de Skills — Ingestion

Todas as Skills de ingestão consomem a API-Football v3 e gravam JSON bruto na Bronze (Databricks Delta).

---

### 4.1 `mcp/skills/ingestion/api_football_base.py`

**Propósito**: Classe base para todas as Skills que consomem a API-Football. Contém a lógica compartilhada de autenticação, rate limiting e tratamento de resposta.

**Implementar**:
- Classe `APIFootballBaseSkill(MCPSkill)`.
- Base URL: `https://v3.football.api-sports.io`.
- Header de auth: `x-apisports-key` com valor do `context.api_football_key`.
- Método `_make_request(endpoint, params) → dict`: faz GET, trata status HTTP, extrai `response` do JSON, registra headers de quota (`x-ratelimit-requests-remaining`).
- Método `_check_quota(response_headers)`: verifica remaining > 0, levanta `MCPQuotaExceededError` se esgotado.
- Método `_write_to_bronze(data, table_name, context)`: escreve lista de dicts como JSON string em tabela Delta Bronze, adicionando `_ingestion_date`, `_ingestion_ts`, `_batch_id`, `_source_endpoint`.
- Rate limiting: sleep de `60 / requests_per_minute` entre chamadas.
- Retry: tenacity com 3 tentativas, exponential backoff, retry em HTTP 429 e 500.

---

### 4.2 `mcp/skills/ingestion/api_football_fixtures.py`

**Propósito**: Extrair partidas do endpoint `/fixtures`.

**Implementar**:
- Classe `APIFootballFixturesExtractor(APIFootballBaseSkill)`.
- name: `api_football_fixtures_extractor`.
- validate: verificar que `context.api_football_key` existe e `league_ids` está definido.
- execute:
  - Para cada league_id em `context.params["league_ids"]`:
    - Chamar `/fixtures?league={league_id}&season={season}&from={date}&to={date}`.
    - Modo incremental: `from` = última data de ingestão, `to` = hoje.
    - Modo backfill: `from` e `to` do params.
  - Gravar em `bronze.football_fixtures_raw`.
  - Retornar SkillResult com total de fixtures coletados.
- Parâmetros do context.params: `league_ids` (list), `season` (int), `from_date` (str optional), `to_date` (str optional), `mode` (incremental/backfill).

---

### 4.3 `mcp/skills/ingestion/api_football_statistics.py`

**Propósito**: Extrair estatísticas de partida do endpoint `/fixtures/statistics`.

**Implementar**:
- Classe `APIFootballStatisticsExtractor(APIFootballBaseSkill)`.
- name: `api_football_statistics_extractor`.
- execute:
  - Receber lista de `fixture_ids` do `context.artifacts` (preenchido pela Skill anterior) ou do params.
  - Para cada fixture_id: chamar `/fixtures/statistics?fixture={fixture_id}`.
  - Otimização: usar batch de IDs se a API suportar.
  - Gravar em `bronze.football_statistics_raw`.
- Dependência: requer que `api_football_fixtures_extractor` tenha executado antes (fixture_ids no artifacts).

---

### 4.4 `mcp/skills/ingestion/api_football_events.py`

**Propósito**: Extrair eventos (gols, cartões, substituições) de `/fixtures/events`.

**Implementar**:
- Classe `APIFootballEventsExtractor(APIFootballBaseSkill)`.
- name: `api_football_events_extractor`.
- Lógica similar a statistics: iterar sobre fixture_ids.
- Gravar em `bronze.football_events_raw`.

---

### 4.5 `mcp/skills/ingestion/api_football_lineups.py`

**Propósito**: Extrair escalações de `/fixtures/lineups`.

**Implementar**:
- Classe `APIFootballLineupsExtractor(APIFootballBaseSkill)`.
- name: `api_football_lineups_extractor`.
- Gravar em `bronze.football_lineups_raw`.

---

### 4.6 `mcp/skills/ingestion/api_football_players.py`

**Propósito**: Extrair stats de jogadores por partida de `/fixtures/players`.

**Implementar**:
- Classe `APIFootballPlayersExtractor(APIFootballBaseSkill)`.
- name: `api_football_players_extractor`.
- Gravar em `bronze.football_players_stats_raw`.

---

### 4.7 `mcp/skills/ingestion/api_football_odds.py`

**Propósito**: Extrair odds pré-jogo de `/odds`.

**Implementar**:
- Classe `APIFootballOddsExtractor(APIFootballBaseSkill)`.
- name: `api_football_odds_extractor`.
- execute:
  - Chamar `/odds?fixture={fixture_id}&bookmaker=...` para cada fixture futuro ou recém-completado.
  - Filtrar mercado "Match Winner" (1X2) como principal.
  - Coletar também Over/Under 2.5 e BTTS se disponíveis.
  - Gravar em `bronze.football_odds_raw`.

---

### 4.8 `mcp/skills/ingestion/api_football_standings.py`

**Propósito**: Extrair classificação de `/standings`.

**Implementar**:
- Classe `APIFootballStandingsExtractor(APIFootballBaseSkill)`.
- name: `api_football_standings_extractor`.
- execute: chamar `/standings?league={league_id}&season={season}`.
- Gravar em `bronze.football_standings_raw`.

---

### 4.9 `mcp/skills/ingestion/api_football_injuries.py`

**Propósito**: Extrair lesões de `/injuries`.

**Implementar**:
- Classe `APIFootballInjuriesExtractor(APIFootballBaseSkill)`.
- name: `api_football_injuries_extractor`.
- Gravar em `bronze.football_injuries_raw`.

---

### 4.10 `mcp/skills/ingestion/api_football_predictions.py`

**Propósito**: Extrair predições da API de `/predictions`.

**Implementar**:
- Classe `APIFootballPredictionsExtractor(APIFootballBaseSkill)`.
- name: `api_football_predictions_extractor`.
- Gravar em `bronze.football_predictions_raw`.
- Estas predições da API são features para o modelo próprio, não substituem o modelo.

---

### 4.11 `mcp/skills/ingestion/api_football_teams.py`

**Propósito**: Extrair dados cadastrais de times de `/teams`.

**Implementar**:
- Classe `APIFootballTeamsExtractor(APIFootballBaseSkill)`.
- name: `api_football_teams_extractor`.
- Frequência: semanal (dados mudam raramente).
- Gravar em `bronze.football_teams_raw`.

---

### 4.12 `mcp/skills/ingestion/api_football_leagues.py`

**Propósito**: Extrair ligas e cobertura de `/leagues`.

**Implementar**:
- Classe `APIFootballLeaguesExtractor(APIFootballBaseSkill)`.
- name: `api_football_leagues_extractor`.
- Frequência: semanal.
- Gravar em `bronze.football_leagues_raw`.
- Extrair campo `coverage` para saber quais features cada liga suporta.

---

### 4.13 `mcp/skills/ingestion/api_football_quota_monitor.py`

**Propósito**: Monitorar consumo de quota da API.

**Implementar**:
- Classe `APIFootballQuotaMonitor(MCPSkill)`.
- name: `api_football_quota_monitor`.
- execute: ler headers `x-ratelimit-requests-limit` e `x-ratelimit-requests-remaining` do último request.
- Calcular percentual consumido.
- Se > 80%: registrar warning no log.
- Se > 95%: registrar error e adicionar flag `quota_critical` no artifacts.
- Gravar métricas de quota na tabela `audit.pipeline_execution`.

---

## 5. Camada de Skills — Processing

Skills que transformam Bronze → Silver no Databricks Spark.

---

### 5.1 `mcp/skills/processing/spark_football_fixtures_flatten.py`

**Propósito**: Flatten do JSON de fixtures, extrair campos tipados, deduplicar.

**Implementar**:
- Classe `SparkFootballFixturesFlatten(MCPSkill)`.
- name: `spark_football_fixtures_flatten`.
- validate: verificar SparkSession no context.
- execute:
  - Ler `bronze.football_fixtures_raw` filtrado por `_ingestion_date`.
  - Parsear JSON do payload.
  - Extrair campos: fixture_id, league_id, season, match_date (cast DATE), home_team_id, away_team_id, goals_home, goals_away, status, venue, referee, round.
  - Calcular `result`: H se goals_home > goals_away, D se igual, A se menor (apenas para status FT).
  - Deduplicar por fixture_id (manter mais recente por `_ingestion_ts`).
  - MERGE em `silver.football_fixtures`.
  - OPTIMIZE com ZORDER BY (fixture_id, league_id).
- Particionamento Silver: `match_date`.

---

### 5.2 `mcp/skills/processing/spark_football_statistics_flatten.py`

**Propósito**: Normalizar statistics — pivot de tipos de stat para colunas.

**Implementar**:
- Classe `SparkFootballStatisticsFlatten(MCPSkill)`.
- name: `spark_football_statistics_flatten`.
- execute:
  - Ler `bronze.football_statistics_raw`.
  - JSON da API retorna array de `{type, value}` por time. Fazer pivot para colunas: shots_on_goal, shots_off_goal, total_shots, blocked_shots, shots_inside_box, shots_outside_box, fouls, corner_kicks, offsides, ball_possession, yellow_cards, red_cards, goalkeeper_saves, total_passes, passes_accurate, passes_pct, expected_goals.
  - Gravar em `silver.football_match_statistics` com PK (fixture_id, team_id).
  - ZORDER BY (fixture_id, team_id).

---

### 5.3 `mcp/skills/processing/spark_football_events_normalize.py`

**Propósito**: Normalizar eventos com classificação por tipo.

**Implementar**:
- Classe `SparkFootballEventsNormalize(MCPSkill)`.
- name: `spark_football_events_normalize`.
- execute:
  - Extrair: fixture_id, team_id, player_id, event_type (Goal, Card, Subst, Var), event_detail (Normal Goal, Yellow Card, Red Card, Penalty, Own Goal, etc.), time_elapsed, time_extra.
  - Gravar em `silver.football_match_events`.

---

### 5.4 `mcp/skills/processing/spark_football_odds_normalize.py`

**Propósito**: Consolidar odds por bookmaker, normalizar mercados.

**Implementar**:
- Classe `SparkFootballOddsNormalize(MCPSkill)`.
- name: `spark_football_odds_normalize`.
- execute:
  - Ler `bronze.football_odds_raw`.
  - Filtrar mercado "Match Winner" (bet_name com Home/Draw/Away).
  - Extrair: fixture_id, bookmaker_name, bookmaker_id, odd_home, odd_draw, odd_away, match_date.
  - Gravar em `silver.football_odds_prematch`.
  - ZORDER BY (fixture_id, bookmaker_name).

---

### 5.5 `mcp/skills/processing/spark_football_dedup.py`

**Propósito**: Deduplicação global em todas as tabelas Silver.

**Implementar**:
- Classe `SparkFootballDedup(MCPSkill)`.
- name: `spark_football_dedup`.
- execute:
  - Para cada tabela Silver configurada:
    - Identificar PK (fixture_id, ou fixture_id + team_id, etc.).
    - Remover duplicatas mantendo registro mais recente por `_loaded_at`.
  - Registrar quantidade de duplicatas removidas no SkillResult.

---

### 5.6 `mcp/skills/processing/spark_football_key_generator.py`

**Propósito**: Criar surrogate keys compostas onde necessário.

**Implementar**:
- Classe `SparkFootballKeyGenerator(MCPSkill)`.
- name: `spark_football_key_generator`.
- execute: gerar MD5 hash de chaves compostas (ex: `fixture_id || team_id` → `match_stat_key`) e adicionar como coluna nas tabelas Silver que precisam.

---

## 6. Camada de Skills — dbt

---

### 6.1 `mcp/skills/dbt/dbt_football_run.py`

**Propósito**: Executar modelos dbt para o domínio football.

**Implementar**:
- Classe `DBTFootballRunSkill(MCPSkill)`.
- name: `dbt_football_run`.
- execute:
  - Executar `dbt run --project-dir {path} --target {target} --select tag:football --log-format json`.
  - Capturar stdout/stderr.
  - Parsear resultado JSON para contar modelos executados com sucesso vs erro.
  - Retornar SkillResult com contagem.

---

### 6.2 `mcp/skills/dbt/dbt_football_test.py`

**Propósito**: Rodar todos os testes (unit + schema + singular) do domínio football.

**Implementar**:
- Classe `DBTFootballTestSkill(MCPSkill)`.
- name: `dbt_football_test`.
- execute:
  - Executar `dbt test --project-dir {path} --target {target} --select tag:football`.
  - Parsear resultados: pass/fail/warn/error.
  - Se algum teste falhar com severity error: retornar SkillResult com success=False.
  - Se apenas warnings: retornar success=True com warnings no message.

---

### 6.3 `mcp/skills/dbt/dbt_football_docs.py`

**Propósito**: Gerar documentação e lineage graph.

**Implementar**:
- Classe `DBTFootballDocsSkill(MCPSkill)`.
- name: `dbt_football_docs`.
- execute: `dbt docs generate --project-dir {path} --target {target}`.
- Frequência: semanal (não precisa rodar todo dia).

---

## 7. Camada de Skills — ML

---

### 7.1 `mcp/skills/ml/ml_feature_store_loader.py`

**Propósito**: Carregar `fct_match_features` da Gold para formato de treino.

**Implementar**:
- Classe `MLFeatureStoreLoader(MCPSkill)`.
- name: `ml_feature_store_loader`.
- execute:
  - Ler `gold.fct_match_features` via Spark ou Databricks SQL.
  - Filtrar apenas partidas com `result IS NOT NULL` (já realizadas) para treino.
  - Filtrar partidas com `result IS NULL` (futuras) para predição.
  - Converter para Pandas DataFrame.
  - Separar X (features) e y (target: result).
  - Armazenar em `context.artifacts["train_data"]` e `context.artifacts["predict_data"]`.
  - Retornar contagem de samples de treino e predição.

**Features a incluir** (conforme PRD, 11 grupos):
- home_wins_last_5, home_draws_last_5, home_losses_last_5, home_goals_scored_avg_5, home_goals_conceded_avg_5.
- away_wins_last_5, away_draws_last_5, away_losses_last_5, away_goals_scored_avg_5, away_goals_conceded_avg_5.
- home_elo_rating, away_elo_rating, elo_diff.
- h2h_home_wins, h2h_draws, h2h_away_wins.
- odd_home_avg, odd_draw_avg, odd_away_avg.
- home_position, away_position, position_diff.
- home_injuries_count, away_injuries_count.
- api_pred_home_pct, api_pred_draw_pct, api_pred_away_pct.
- is_derby, days_since_last_match_home, days_since_last_match_away.

---

### 7.2 `mcp/skills/ml/ml_model_training.py`

**Propósito**: Treinar o stacking ensemble.

**Implementar**:
- Classe `MLModelTraining(MCPSkill)`.
- name: `ml_model_training`.
- execute:
  - Receber train_data do `context.artifacts`.
  - Label encode target: H=0, D=1, A=2.
  - Time-series split: ordenar por match_date, usar últimos N% como validação.
  - Treinar modelos base via cross-validation:
    - RandomForestClassifier (n_estimators=500, max_depth=12).
    - XGBClassifier (n_estimators=500, max_depth=6, learning_rate=0.05).
    - LGBMClassifier (n_estimators=500, max_depth=8, learning_rate=0.05).
  - Gerar out-of-fold predictions dos 3 modelos.
  - Treinar meta-learner: LogisticRegression com calibração (CalibratedClassifierCV).
  - Armazenar pipeline completo em `context.artifacts["trained_model"]`.
  - Armazenar métricas em `context.artifacts["model_metrics"]`.

---

### 7.3 `mcp/skills/ml/ml_model_evaluation.py`

**Propósito**: Avaliar o modelo treinado e decidir se promove.

**Implementar**:
- Classe `MLModelEvaluation(MCPSkill)`.
- name: `ml_model_evaluation`.
- execute:
  - Calcular métricas no validation set:
    - Log Loss (métrica primária).
    - Accuracy.
    - Brier Score (por classe).
    - ROC AUC (one-vs-rest).
  - Comparar log_loss com modelo em produção (buscar do MLflow).
  - Decisão: promover se `new_log_loss < current_log_loss` ou se não há modelo em produção.
  - Armazenar decisão em `context.artifacts["should_promote"]` (bool).

---

### 7.4 `mcp/skills/ml/ml_model_registry.py`

**Propósito**: Registrar modelo no MLflow com métricas e artefatos.

**Implementar**:
- Classe `MLModelRegistry(MCPSkill)`.
- name: `ml_model_registry`.
- execute:
  - Conectar ao MLflow Tracking Server.
  - Criar experiment "football-prediction-engine".
  - Logar:
    - Parâmetros: hiperparâmetros dos 3 modelos + meta-learner.
    - Métricas: log_loss, accuracy, brier_score, roc_auc.
    - Artefatos: modelo serializado (joblib), feature importance plot, confusion matrix.
    - Tags: league_ids, season, training_date.
  - Se `should_promote == True`: registrar como nova versão do modelo "football-match-predictor" e transicionar para stage "Production".
  - Gerar `model_version` string (ex: v1.3.2 baseado em semantic versioning).

---

### 7.5 `mcp/skills/ml/ml_prediction_generator.py`

**Propósito**: Gerar probabilidades para partidas futuras.

**Implementar**:
- Classe `MLPredictionGenerator(MCPSkill)`.
- name: `ml_prediction_generator`.
- execute:
  - Carregar modelo em produção do MLflow (stage "Production").
  - Receber predict_data do `context.artifacts`.
  - Gerar `predict_proba` → (prob_home, prob_draw, prob_away) para cada fixture.
  - Calcular confidence: "high" se max_prob > 0.55, "medium" se > 0.40, "low" se <= 0.40.
  - Armazenar DataFrame de predições em `context.artifacts["predictions"]`.
  - Retornar contagem de predições geradas.

---

### 7.6 `mcp/skills/ml/ml_prediction_writer.py`

**Propósito**: Escrever predições na Gold (Delta).

**Implementar**:
- Classe `MLPredictionWriter(MCPSkill)`.
- name: `ml_prediction_writer`.
- execute:
  - Converter predictions para Spark DataFrame.
  - MERGE em `gold.fct_match_predictions` por fixture_id.
  - Adicionar: model_version, generated_at, _loaded_at.
  - OPTIMIZE com ZORDER BY (fixture_id, model_version).

---

## 8. Camada de Skills — Serving

---

### 8.1 `mcp/skills/serving/postgres_predictions_upsert.py`

**Propósito**: UPSERT predições no PostgreSQL serving.

**Implementar**:
- Classe `PostgresPredictionsUpsert(MCPSkill)`.
- name: `postgres_predictions_upsert`.
- execute:
  - Conectar a postgres-serving:5432.
  - Ler predições do `context.artifacts` ou direto da Gold.
  - INSERT INTO serving.match_predictions ... ON CONFLICT (fixture_id) DO UPDATE SET.
  - INSERT append em serving.historical_predictions (preservar todas as versões).
  - Registrar em audit.pipeline_execution.

---

### 8.2–8.4: Demais Skills de Serving

Seguem mesmo padrão do 8.1, cada uma para sua tabela:
- `postgres_standings_upsert.py` → `serving.league_standings`.
- `postgres_team_form_upsert.py` → `serving.team_form`.
- `postgres_fixtures_upsert.py` → `serving.upcoming_fixtures`.

---

### 8.5 `mcp/skills/serving/cache_invalidator.py`

**Propósito**: Invalidar cache após atualização de dados.

**Implementar**:
- Classe `CacheInvalidator(MCPSkill)`.
- name: `cache_invalidator`.
- execute:
  - REFRESH MATERIALIZED VIEW CONCURRENTLY serving.mv_round_predictions.
  - REFRESH MATERIALIZED VIEW CONCURRENTLY serving.mv_model_accuracy_trend.
  - Opcionalmente: invalidar cache Redis se API usar caching.

---

## 9. Camada de Skills — Quality

---

### 9.1–9.5: Skills de Qualidade

| Arquivo                            | name                        | O que valida                                              |
|------------------------------------|-----------------------------|-----------------------------------------------------------|
| quality_fixture_count_check.py     | quality_fixture_count_check | Rodada tem N jogos esperados (10 para Série A, etc.)      |
| quality_odds_range_check.py        | quality_odds_range_check    | Todas odds entre 1.01 e 100.00                            |
| quality_prediction_sum_check.py    | quality_prediction_sum_check| prob_home + prob_draw + prob_away entre 0.95 e 1.05       |
| quality_freshness_check.py         | quality_freshness_check     | Dados mais recentes com menos de 24h de defasagem         |
| quality_model_drift_check.py       | quality_model_drift_check   | Acurácia das últimas 50 predições não caiu > 10% vs média |

Cada uma segue o contrato MCPSkill: validate → execute → SkillResult (success=True/False).

---

## 10. Camada de Agents

---

### 10.1 `agents/base_agent.py`

**Propósito**: Agent base com padrão de execução, retry e logging.

**Implementar**:
- Classe `BaseAgent` com:
  - Construtor: recebe lista de Skills e max_retries (default 2).
  - Método `execute(context) → list[SkillResult]`:
    - Iterar sobre Skills na ordem definida.
    - Para cada Skill: log início → validate → execute com retry → log resultado.
    - Se Skill falhar: invocar rollback, logar erro, levantar RuntimeError (fail-fast).
  - Método `_execute_with_retry(skill, context)`: loop de tentativas com exponential backoff.
  - Logging via structlog com campos: agent_name, skill_name, skill_version, run_id, duration_ms.

---

### 10.2 `agents/football_ingestion_agent.py`

**Propósito**: Orquestra todas as Skills de ingestão da API-Football.

**Implementar**:
- Classe `FootballIngestionAgent(BaseAgent)`.
- Construtor: instanciar e ordenar Skills:
  1. api_football_leagues_extractor
  2. api_football_fixtures_extractor
  3. api_football_statistics_extractor
  4. api_football_events_extractor
  5. api_football_lineups_extractor
  6. api_football_players_extractor
  7. api_football_odds_extractor
  8. api_football_standings_extractor
  9. api_football_injuries_extractor
  10. api_football_predictions_extractor
  11. api_football_teams_extractor
  12. api_football_quota_monitor
- max_retries: 3 (API pode ter instabilidade).

---

### 10.3 `agents/football_processing_agent.py`

**Propósito**: Orquestra transformações Bronze → Silver.

**Implementar**:
- Classe `FootballProcessingAgent(BaseAgent)`.
- Skills na ordem:
  1. spark_football_fixtures_flatten
  2. spark_football_statistics_flatten
  3. spark_football_events_normalize
  4. spark_football_odds_normalize
  5. spark_football_key_generator
  6. spark_football_dedup
- max_retries: 2.

---

### 10.4 `agents/football_dbt_agent.py`

**Propósito**: Executar dbt run + test.

**Implementar**:
- Classe `FootballDBTAgent(BaseAgent)`.
- Skills:
  1. dbt_football_run
  2. dbt_football_test
- max_retries: 1 (dbt é determinístico — se falhar, é por erro real).

---

### 10.5 `agents/football_ml_agent.py`

**Propósito**: Pipeline completo de ML.

**Implementar**:
- Classe `FootballMLAgent(BaseAgent)`.
- Skills para pipeline diário (predição apenas):
  1. ml_feature_store_loader
  2. ml_prediction_generator
  3. ml_prediction_writer
- Skills para pipeline semanal (retreino completo):
  1. ml_feature_store_loader
  2. ml_model_training
  3. ml_model_evaluation
  4. ml_model_registry
  5. ml_prediction_generator
  6. ml_prediction_writer
- Lógica no construtor: receber parâmetro `mode` ("predict" ou "retrain") para selecionar Skills.

---

### 10.6 `agents/football_serving_agent.py`

**Propósito**: Carregar dados no PostgreSQL serving.

**Implementar**:
- Classe `FootballServingAgent(BaseAgent)`.
- Skills:
  1. postgres_predictions_upsert
  2. postgres_standings_upsert
  3. postgres_team_form_upsert
  4. postgres_fixtures_upsert
  5. cache_invalidator

---

### 10.7 `agents/football_quality_agent.py`

**Propósito**: Validação de qualidade pós-pipeline.

**Implementar**:
- Classe `FootballQualityAgent(BaseAgent)`.
- Skills:
  1. quality_fixture_count_check
  2. quality_odds_range_check
  3. quality_prediction_sum_check
  4. quality_freshness_check
  5. quality_model_drift_check
- max_retries: 1 (testes de qualidade não se beneficiam de retry).

---

## 11. Camada Airflow — DAGs

---

### 11.1 `airflow/dags/football_daily_pipeline.py`

**Propósito**: Pipeline diário completo.
**Schedule**: `0 6 * * *` (06:00 UTC).

**Implementar**:
- default_args: owner "data-engineering", retries 2, retry_delay 5min, execution_timeout 2h, sla 4h, email_on_failure True.
- Tags: ["football", "production", "daily"].
- catchup: False, max_active_runs: 1.
- Tasks (cada uma um PythonOperator que instancia o Agent e chama execute):
  1. `ingestion_agent` → FootballIngestionAgent.
  2. `processing_agent` → FootballProcessingAgent.
  3. `dbt_agent` → FootballDBTAgent.
  4. `ml_agent` → FootballMLAgent(mode="predict").
  5. `serving_agent` → FootballServingAgent.
  6. `quality_agent` → FootballQualityAgent.
- Dependências: `ingestion >> processing >> dbt >> ml >> serving >> quality`.
- Cada callable constrói ExecutionContext com run_id, execution_date, params (league_ids, season, api_football_key de Airflow Variable).

---

### 11.2 `airflow/dags/football_matchday_pipeline.py`

**Propósito**: Coleta extra em dias de jogo.
**Schedule**: `0 10 * * 3,6,7` (qua, sáb, dom 10:00 UTC).

**Implementar**:
- Mesmo fluxo do daily, mas com params adicionais:
  - `mode: incremental`.
  - `include_lineups: True` (escalações confirmadas).
  - `include_injuries: True` (atualização pré-jogo).
- Skills de ingestão filtradas: apenas fixtures, lineups, injuries, odds.

---

### 11.3 `airflow/dags/football_weekly_retrain.py`

**Propósito**: Retreinar modelo ML.
**Schedule**: `0 4 * * 1` (toda segunda 04:00 UTC).

**Implementar**:
- Tasks:
  1. `ml_retrain_agent` → FootballMLAgent(mode="retrain").
  2. `serving_metrics_update` → atualizar serving.model_metrics.
  3. `notification` → Slack com resultado do retreino.

---

### 11.4 `airflow/dags/football_weekly_maintenance.py`

**Propósito**: OPTIMIZE + VACUUM + ANALYZE.
**Schedule**: `0 2 * * 0` (todo domingo 02:00 UTC).

**Implementar**:
- Task única: DatabricksSubmitRunOperator executando `maintenance/optimize_football_tables.py`.
- Tabelas e ZORDER conforme PRD Football (seção 5.3).

---

### 11.5 `airflow/dags/football_season_init.py`

**Propósito**: Backfill de temporada nova.
**Schedule**: Manual (trigger manual).

**Implementar**:
- Parâmetros de input: league_id, season, from_date, to_date.
- Executa FootballIngestionAgent com mode="backfill".
- Seguido de processing → dbt → ml(retrain) → serving.

---

## 12. Camada Databricks — Schemas DDL

---

### 12.1 `databricks/schemas/01_create_catalog.sql`

**Implementar**:
- CREATE CATALOG IF NOT EXISTS mcp_platform.
- USE CATALOG mcp_platform.
- CREATE SCHEMA IF NOT EXISTS bronze COMMENT 'Raw data layer'.
- CREATE SCHEMA IF NOT EXISTS silver COMMENT 'Cleaned data layer'.
- CREATE SCHEMA IF NOT EXISTS gold COMMENT 'Business-ready marts'.
- CREATE SCHEMA IF NOT EXISTS snapshots COMMENT 'dbt snapshots SCD2'.

---

### 12.2 `databricks/schemas/02_bronze_ddl.sql`

**Implementar**: 15 tabelas Bronze conforme PRD seção 5.1.

Padrão para cada tabela:
- Campos: payload (STRING — JSON raw), endpoint (STRING), _ingestion_date (DATE), _ingestion_ts (TIMESTAMP), _batch_id (STRING), _source_endpoint (STRING).
- PK implícita: sem constraint no Delta, mas dedup pelo processing.
- USING DELTA, PARTITIONED BY (_ingestion_date).
- TBLPROPERTIES: autoOptimize.optimizeWrite, autoOptimize.autoCompact, logRetentionDuration 30 days, quality bronze.

Tabelas: football_fixtures_raw, football_statistics_raw, football_events_raw, football_lineups_raw, football_players_stats_raw, football_odds_raw, football_odds_live_raw, football_predictions_raw, football_standings_raw, football_teams_raw, football_players_raw, football_injuries_raw, football_coaches_raw, football_transfers_raw, football_leagues_raw.

---

### 12.3 `databricks/schemas/03_silver_ddl.sql`

**Implementar**: 14 tabelas Silver conforme PRD seção 5.1.

Cada tabela com campos tipados (INT, STRING, DATE, TIMESTAMP, DECIMAL), PARTITION BY e ZORDER conforme tabela do PRD seção 5.3. Metadados: _loaded_at (TIMESTAMP), _batch_id (STRING).

Tabelas e seus campos principais:

**football_fixtures**: fixture_id INT, league_id INT, season INT, round STRING, match_date DATE, match_time STRING, venue STRING, referee STRING, home_team_id INT, away_team_id INT, goals_home INT, goals_away INT, halftime_home INT, halftime_away INT, status STRING, result STRING (H/D/A/NULL). PARTITION BY match_date, ZORDER BY (fixture_id, league_id).

**football_match_statistics**: fixture_id INT, team_id INT, shots_on_goal INT, shots_off_goal INT, total_shots INT, blocked_shots INT, fouls INT, corner_kicks INT, offsides INT, ball_possession DECIMAL(5,2), yellow_cards INT, red_cards INT, goalkeeper_saves INT, total_passes INT, passes_accurate INT, passes_pct DECIMAL(5,2), expected_goals DECIMAL(4,2). PARTITION BY match_date, ZORDER BY (fixture_id, team_id).

**football_match_events**: fixture_id INT, team_id INT, player_id INT, event_type STRING, event_detail STRING, time_elapsed INT, time_extra INT, comments STRING. PARTITION BY match_date, ZORDER BY (fixture_id, event_type).

**football_match_lineups**: fixture_id INT, team_id INT, formation STRING, player_id INT, player_name STRING, player_number INT, player_position STRING, is_starter BOOLEAN. PARTITION BY match_date, ZORDER BY (fixture_id, team_id).

**football_player_match_stats**: fixture_id INT, team_id INT, player_id INT, minutes_played INT, rating DECIMAL(3,1), goals INT, assists INT, shots_total INT, shots_on INT, passes_total INT, passes_key INT, passes_accuracy DECIMAL(5,2), tackles INT, interceptions INT, duels_won INT, duels_total INT, dribbles_won INT, fouls_committed INT, fouls_drawn INT, yellow_cards INT, red_cards INT. PARTITION BY match_date, ZORDER BY (fixture_id, player_id).

**football_odds_prematch**: fixture_id INT, bookmaker_name STRING, bookmaker_id INT, odd_home DECIMAL(6,2), odd_draw DECIMAL(6,2), odd_away DECIMAL(6,2), odd_over25 DECIMAL(6,2), odd_under25 DECIMAL(6,2), odd_btts_yes DECIMAL(6,2), odd_btts_no DECIMAL(6,2), match_date DATE, _collected_at TIMESTAMP. PARTITION BY match_date, ZORDER BY (fixture_id, bookmaker_name).

**football_standings**: league_id INT, season INT, team_id INT, position INT, team_name STRING, played INT, wins INT, draws INT, losses INT, goals_for INT, goals_against INT, goal_diff INT, points INT, form STRING, description STRING, _snapshot_date DATE. PARTITION BY season, ZORDER BY (league_id, team_id).

**football_teams**: team_id INT, team_name STRING, team_code STRING, country STRING, founded INT, logo_url STRING, venue_name STRING, venue_city STRING, venue_capacity INT. ZORDER BY (team_id, country).

**football_players**: player_id INT, player_name STRING, firstname STRING, lastname STRING, age INT, birth_date DATE, nationality STRING, height STRING, weight STRING, team_id INT, season INT, position STRING, photo_url STRING. PARTITION BY season, ZORDER BY (player_id, team_id).

**football_injuries**: player_id INT, team_id INT, fixture_id INT, league_id INT, season INT, injury_type STRING, injury_reason STRING, match_date DATE. PARTITION BY match_date, ZORDER BY (team_id, player_id).

**football_leagues**: league_id INT, league_name STRING, league_type STRING (league/cup), country STRING, country_code STRING, season INT, season_start DATE, season_end DATE, has_standings BOOLEAN, has_events BOOLEAN, has_lineups BOOLEAN, has_statistics BOOLEAN, has_players BOOLEAN, has_predictions BOOLEAN, has_odds BOOLEAN. ZORDER BY (league_id).

**football_api_predictions**: fixture_id INT, match_date DATE, pred_winner_id INT, pred_winner_name STRING, pred_winner_comment STRING, pred_home_pct STRING, pred_draw_pct STRING, pred_away_pct STRING, pred_advice STRING, pred_under_over STRING, pred_goals_home STRING, pred_goals_away STRING. PARTITION BY match_date, ZORDER BY (fixture_id).

**football_transfers**: player_id INT, player_name STRING, from_team_id INT, from_team_name STRING, to_team_id INT, to_team_name STRING, transfer_date DATE, transfer_type STRING. ZORDER BY (player_id).

---

### 12.4 `databricks/schemas/04_gold_ddl.sql`

**Implementar**: 14 tabelas Gold conforme PRD seções 5.1 e 7.1.

Tabelas com campos já especificados no PRD. PARTITION BY e ZORDER conforme tabela PRD seção 5.3. TBLPROPERTIES com quality gold, logRetentionDuration 90 days.

As tabelas Gold são criadas automaticamente pelo dbt (materialized table) — este DDL serve como referência e fallback manual.

---

## 13. Camada dbt — Todos os Modelos

---

### 13.1 `dbt_project/dbt_project.yml`

**Implementar**:
- name: football_analytics, version 1.0.0, config-version 2, profile football_databricks.
- Models: staging (+materialized view, +schema staging, +tags ["staging", "football"]), intermediate (+materialized ephemeral, +tags ["intermediate", "football"]), mart (+materialized table, +schema gold, +tags ["mart", "football"]).
- vars: start_date "2024-01-01", brasileirao_league_id 71, current_season 2025, elo_initial_rating 1500, elo_k_factor 20, form_window 5.

---

### 13.2 `dbt_project/profiles.yml`

**Implementar**:
- Profile football_databricks com targets dev, staging, prod.
- Cada target: type databricks, catalog mcp_platform, host/http_path/token via env_var.
- Threads: dev=4, staging=8, prod=16.

---

### 13.3 `dbt_project/packages.yml`

**Implementar**:
- dbt-labs/dbt_utils 1.2.0.
- calogica/dbt_expectations 0.10.3.
- dbt-labs/codegen 0.12.1.

---

### 13.4 `dbt_project/models/staging/football/_football_sources.yml`

**Implementar**:
- Declarar sources para cada tabela Silver (schema silver no catalog mcp_platform).
- Freshness checks: warn_after 12h, error_after 24h para fixtures e statistics.
- Column tests básicos: not_null em fixture_id, team_id, league_id.

---

### 13.5 Staging Models (8 arquivos)

Cada staging model: view, lê do source Silver, renomeia campos se necessário, aplica filtros básicos e COALESCE para nulls.

| Arquivo                              | Source Silver                   | Função                              |
|--------------------------------------|---------------------------------|-------------------------------------|
| stg_football_fixtures.sql            | football_fixtures               | Filtrar status, cast types          |
| stg_football_match_statistics.sql    | football_match_statistics       | COALESCE stats com 0               |
| stg_football_match_events.sql        | football_match_events           | Classificar event_type              |
| stg_football_odds_prematch.sql       | football_odds_prematch          | Filtrar odds > 1.0                  |
| stg_football_standings.sql           | football_standings              | Snapshot mais recente por liga       |
| stg_football_injuries.sql            | football_injuries               | Filtrar lesões ativas               |
| stg_football_players.sql             | football_players                | Jogadores da temporada atual        |
| stg_football_api_predictions.sql     | football_api_predictions        | Parsear percentuais para DECIMAL    |

---

### 13.6 Intermediate Models (6 arquivos)

Todos ephemeral — não geram tabela. Contêm a lógica de negócio complexa.

**int_football_team_form.sql**: calcular forma recente (últimos N jogos configurável via var). Window function ROWS BETWEEN {form_window - 1} PRECEDING AND CURRENT ROW, particionado por team_id, ordenado por match_date. Calcular wins, draws, losses, goals_scored_avg, goals_conceded_avg, points, form_string (ex: "WDWWL").

**int_football_elo_ratings.sql**: cálculo ELO incremental. Lógica: para cada partida em ordem cronológica, calcular expected score (1 / (1 + 10^((rating_away - rating_home - 100) / 400))), atualizar ratings com K * (actual - expected) * ln(goal_diff + 1). Usar macro `calculate_elo`. Este é o modelo mais complexo — pode precisar ser incremental table em vez de ephemeral se o volume for grande.

**int_football_head_to_head.sql**: para cada par de times, calcular histórico de confrontos diretos (últimos 10 jogos): wins_home, wins_away, draws, goals_avg_home, goals_avg_away.

**int_football_odds_consensus.sql**: agregar odds de todos os bookmakers por fixture_id. Calcular AVG, MEDIAN, MAX, MIN de odd_home, odd_draw, odd_away. Calcular implied probability (1/odd) e normalizar para somar 1.

**int_football_player_impact.sql**: para cada jogador, calcular métricas agregadas: goals_per_90, assists_per_90, rating_avg, minutes_played_pct. Identificar "key players" (top 5 por team por goals+assists).

**int_football_match_context.sql**: derivar variáveis de contexto. is_derby (lookup de derbies conhecidos via seed), days_since_last_match (DATEDIFF com partida anterior do time), is_cup_match (league_type = 'cup').

---

### 13.7 Mart Models (14 arquivos)

Todos materialized table em Delta, com PARTITION BY e ZORDER via post_hook.

**fct_match_features.sql**: JOIN de todos os intermediates + staging para montar a feature matrix completa. Uma linha por fixture_id. Features dos 11 grupos do PRD seção 7.1. PARTITION BY season, ZORDER BY (fixture_id, league_id). Esta tabela é o input direto do ML.

**fct_team_form.sql**: forma recente materializada por time/season. PARTITION BY season, ZORDER BY (team_id, league_id).

**fct_team_strength.sql**: ELO rating atual por time. ZORDER BY (team_id).

**fct_head_to_head.sql**: confrontos diretos materializado. ZORDER BY (home_team_id, away_team_id).

**fct_player_impact.sql**: impacto estatístico por jogador/season. PARTITION BY season, ZORDER BY (player_id, team_id).

**fct_odds_consensus.sql**: odds consolidadas por partida. PARTITION BY match_date, ZORDER BY (fixture_id).

**fct_match_predictions.sql**: tabela de predições (populada pelo ML, não pelo dbt). PARTITION BY match_date, ZORDER BY (fixture_id, model_version). O dbt cria a estrutura; o ML Agent popula.

**fct_model_performance.sql**: métricas de performance por model_version. ZORDER BY (model_version).

**fct_league_summary.sql**: resumo por rodada/liga — total de gols, média, distribuição H/D/A. PARTITION BY season, ZORDER BY (league_id).

**fct_team_season_stats.sql**: stats acumuladas por time na temporada. PARTITION BY season, ZORDER BY (team_id).

**dim_teams.sql**: dimensão times enriquecida (nome, país, venue, capacidade, logo). ZORDER BY (team_id).

**dim_leagues.sql**: dimensão ligas (nome, país, tipo, cobertura). ZORDER BY (league_id).

**dim_players.sql**: dimensão jogadores (nome, posição, nacionalidade, time atual). PARTITION BY season, ZORDER BY (player_id).

---

### 13.8 Testes dbt

**Unit Tests** (4 arquivos YAML em `tests/unit/`): conforme PRD seção 8.3 — test_fct_team_form (wins+draws+losses = total), test_fct_match_features (no data leakage), test_fct_team_strength (ELO initial 1500, zero-sum), test_fct_odds_consensus (odds > 1.0).

**Singular Tests** (5 arquivos SQL em `tests/singular/`): conforme PRD seção 8.3 — assert_no_future_features, assert_prediction_probabilities_sum, assert_elo_rating_reasonable, assert_no_orphan_statistics, assert_complete_rounds.

**Schema Tests** (em _football_mart_schema.yml): conforme PRD seção 8.3 — not_null, unique, accepted_values, dbt_expectations range checks em todas as tabelas mart.

---

### 13.9 Macros dbt (4 arquivos)

**generate_surrogate_key.sql**: md5(concat_ws de colunas).
**calculate_elo.sql**: macro com lógica de cálculo ELO (expected score, K-factor, goal diff multiplier).
**calculate_form.sql**: macro de window function para forma recente.
**optimize_delta.sql**: macro para OPTIMIZE + ZORDER genérica.

---

### 13.10 Snapshots (2 arquivos)

**snap_standings.sql**: SCD2 de standings por (league_id, team_id, season), strategy check em (position, points, form).
**snap_team_strength.sql**: SCD2 de ELO rating por team_id, strategy check em (elo_rating).

---

### 13.11 Seeds (2 arquivos)

**league_metadata.csv**: league_id, league_name, country, priority (P0/P1/P2/P3), expected_teams, expected_rounds.
**team_aliases.csv**: team_id, alias_name, common_name. Para normalizar nomes de times.

---

## 14. Camada API — FastAPI

---

### 14.1 `api/main.py`

**Propósito**: Entry point da FastAPI.

**Implementar**:
- Criar app FastAPI com title "Football Prediction Engine API", version "1.0.0".
- Incluir routers: predictions, fixtures, standings, teams, model_metrics.
- Middleware CORS.
- Endpoint `/health` retornando status e timestamp.
- Startup event: validar conexão com PostgreSQL serving.

---

### 14.2 `api/config.py`

**Propósito**: Configuração via variáveis de ambiente.

**Implementar**:
- Classe Settings(BaseSettings) com: pg_host, pg_port, pg_database, pg_user, pg_password, api_title, api_version, debug.
- Ler de .env via pydantic-settings.

---

### 14.3 `api/database/connection.py`

**Propósito**: Pool de conexões com PostgreSQL serving.

**Implementar**:
- SQLAlchemy engine com pool_size=10, max_overflow=20.
- SessionLocal factory.
- Dependency `get_db()` para injeção nos routers.

---

### 14.4 `api/schemas/` (5 arquivos)

Modelos Pydantic para request/response:

**prediction.py**: PredictionResponse com fixture_id, league, match_date, home_team, away_team, prediction (prob_home_win, prob_draw, prob_away_win, confidence, model_version, generated_at), context (form, elo, h2h, odds).

**fixture.py**: FixtureResponse com fixture_id, league, match_date, venue, home_team, away_team, status, has_prediction.

**standing.py**: StandingResponse com position, team_name, played, wins, draws, losses, goals_for, goals_against, goal_diff, points, form.

**team.py**: TeamFormResponse com team_name, form_string, wins_last_5, elo_rating.

**model.py**: ModelMetricsResponse com model_version, log_loss, accuracy, brier_score, total_predictions, is_active.

---

### 14.5 `api/routers/` (5 arquivos)

| Arquivo            | Rotas                                                          |
|--------------------|----------------------------------------------------------------|
| predictions.py     | GET /predictions/{fixture_id}, /predictions/league/{league_id}, /predictions/today |
| fixtures.py        | GET /fixtures/upcoming, /fixtures/league/{league_id}/next      |
| standings.py       | GET /standings/{league_id}                                     |
| teams.py           | GET /teams/{team_id}/form                                      |
| model_metrics.py   | GET /model/metrics, /model/history                             |

Cada router: query ao PostgreSQL serving via service layer, retorna schema Pydantic.

---

### 14.6 `api/services/` (3 arquivos)

Camada de serviço entre routers e banco:
- prediction_service.py: queries em serving.match_predictions + join com upcoming_fixtures.
- fixture_service.py: queries em serving.upcoming_fixtures.
- standing_service.py: queries em serving.league_standings.

---

## 15. Testes Python

---

### 15.1 `tests/conftest.py`

**Implementar**:
- Fixtures pytest: mock_context (ExecutionContext com valores de teste), mock_spark (MagicMock de SparkSession), mock_pg (MagicMock de psycopg2 connection), sample_fixtures_json (payload real da API-Football para testes).

---

### 15.2 `tests/unit/test_skills/` (6 arquivos)

| Arquivo                         | O que testa                                                    |
|---------------------------------|----------------------------------------------------------------|
| test_api_football_base.py       | _make_request com mock HTTP, _check_quota, rate limiting       |
| test_api_football_fixtures.py   | validate sem API key, execute com response mock                |
| test_spark_fixtures_flatten.py  | flatten de JSON, cálculo de result (H/D/A), dedup             |
| test_ml_model_training.py       | treino com dados mock, shape de output, métricas calculadas    |
| test_postgres_upsert.py         | UPSERT com mock connection, SQL gerado corretamente            |
| test_quality_checks.py          | odds range, prediction sum, fixture count                      |

---

### 15.3 `tests/unit/test_agents/` (4 arquivos)

| Arquivo                    | O que testa                                              |
|----------------------------|----------------------------------------------------------|
| test_ingestion_agent.py    | Ordem de execução das Skills, fail-fast, rollback        |
| test_processing_agent.py   | Execução sequencial, retry                               |
| test_ml_agent.py           | Mode predict vs retrain, Skills selecionadas             |
| test_serving_agent.py      | Execução completa, cache invalidation                    |

---

### 15.4 `tests/unit/test_api/` (2 arquivos)

| Arquivo                    | O que testa                                              |
|----------------------------|----------------------------------------------------------|
| test_predictions_router.py | GET /predictions/{id} com mock DB, 404 para id inválido  |
| test_fixtures_router.py    | GET /fixtures/upcoming, response format                  |

---

### 15.5 `tests/integration/` (2 arquivos)

| Arquivo                          | O que testa                                        |
|----------------------------------|----------------------------------------------------|
| test_pipeline_e2e.py             | Fluxo completo com DB local (testcontainers)       |
| test_api_football_connection.py  | Conexão real com API-Football (roda manual)        |

---

## 16. Scripts Operacionais

---

| Arquivo                         | Propósito                                              |
|---------------------------------|--------------------------------------------------------|
| scripts/setup_venv.sh           | Criar venv Python 3.12 com todas as dependências       |
| scripts/start_all.sh            | Subir toda stack Docker na ordem correta               |
| scripts/stop_all.sh             | Derrubar toda stack                                    |
| scripts/health_check.sh         | Verificar saúde de todos os serviços                   |
| scripts/init_databricks_schemas.sh | Executar DDLs no Databricks via CLI                 |
| scripts/backfill_season.py      | Script Python para backfill de temporada completa      |
| scripts/seed_league_config.py   | Popular config/leagues.yml com dados da API             |

---

## 17. Configuração

---

### 17.1 `config/leagues.yml`

**Propósito**: Configuração de ligas monitoradas.

**Estrutura**:
- Lista de ligas com: id, name, country, priority, season, expected_teams, expected_rounds, schedule (cron de coleta), active (bool).

---

### 17.2 `config/endpoints.yml`

**Propósito**: Mapa de endpoints da API-Football com rate limits.

**Estrutura**:
- Lista de endpoints com: path, frequency (daily/weekly/matchday), bronze_table, params_template, priority.

---

### 17.3 `config/model_config.yml`

**Propósito**: Hiperparâmetros do modelo ML.

**Estrutura**:
- random_forest: n_estimators, max_depth, min_samples_split.
- xgboost: n_estimators, max_depth, learning_rate, subsample.
- lightgbm: n_estimators, max_depth, learning_rate, num_leaves.
- meta_learner: type (logistic_regression), calibration (isotonic).
- validation: test_size, min_training_samples.
- promotion: max_log_loss_threshold.

---

## 18. Documentação

---

| Arquivo                            | Conteúdo                                                |
|------------------------------------|---------------------------------------------------------|
| docs/architecture.md               | Diagrama de arquitetura com explicação por camada        |
| docs/runbook.md                    | Procedimentos operacionais (deploy, rollback, incident)  |
| docs/data_dictionary.md           | Dicionário de dados de todas as tabelas (Bronze→Gold)   |
| docs/api_reference.md             | Documentação da API REST (endpoints, schemas, exemplos)  |
| docs/adr/001_medallion.md         | ADR: por que Medallion Architecture                      |
| docs/adr/002_agent_pattern.md     | ADR: por que padrão Agent com Skills                     |
| docs/adr/003_elo_rating.md        | ADR: escolha e parametrização do ELO                     |
| docs/adr/004_stacking_ensemble.md | ADR: por que stacking ao invés de modelo único           |
| docs/adr/005_quota_management.md  | ADR: estratégia de gestão de quota da API-Football       |

---

## 19. Variáveis de Ambiente (.env.example)

**Implementar** com todos os campos necessários:
- PostgreSQL (airflow + serving): host, port, user, password, database.
- Redis: host, port, password.
- Airflow: admin_user, admin_password, secret_key.
- Databricks: host, token, http_path, catalog.
- API-Football: api_key, base_url, requests_per_minute.
- MLflow: tracking_uri, artifact_root.
- FastAPI: host, port, debug.
- Platform: environment (dev/staging/prod), log_level.

---

## 20. Makefile

**Targets a implementar**:

| Target          | Comando                                                     |
|-----------------|-------------------------------------------------------------|
| help            | Lista todos os targets                                      |
| network         | docker network create mcp_network                           |
| up              | Sobe toda stack (compose master)                            |
| down            | Derruba toda stack                                          |
| restart         | down + up                                                   |
| logs            | Logs de todos os containers                                 |
| venv            | Cria venv Python 3.12                                       |
| dbt-deps        | Instala dependências dbt                                    |
| dbt-run         | Executa modelos dbt                                         |
| dbt-test        | Executa testes dbt                                          |
| dbt-docs        | Gera e serve documentação                                   |
| dbt-full        | deps + run + test                                           |
| lint            | Roda ruff                                                   |
| test            | Roda pytest                                                 |
| test-unit       | Apenas testes unitários                                     |
| test-integration| Apenas testes de integração                                 |
| health          | Health check de todos os serviços                           |
| clean           | Remove volumes Docker                                       |
| backfill        | Executa backfill de temporada                               |
| api-start       | Sobe FastAPI em modo dev                                    |

---

## 21. Ordem de Implementação Recomendada

A implementação deve seguir esta ordem para garantir que cada camada funcione antes de avançar.

| Fase | O que implementar                                          | Validação                              |
|------|------------------------------------------------------------|----------------------------------------|
| 1    | Docker: postgres + redis + network                         | `make health` — PG e Redis online      |
| 2    | MCP Core: context, skill_base, result, exceptions          | `make test-unit` — imports OK          |
| 3    | Docker: airflow (init + webserver + scheduler)             | http://localhost:8080 — login admin    |
| 4    | Config: .env, leagues.yml, endpoints.yml                   | Variáveis carregadas                   |
| 5    | Skills Ingestion: api_football_base + fixtures             | Teste manual: 1 chamada à API OK      |
| 6    | Agent Ingestion + DAG season_init                          | Backfill de 1 rodada Brasileirão       |
| 7    | Databricks: DDLs Bronze                                    | Tabelas criadas, dados da fase 6 lá   |
| 8    | Skills Processing: fixtures_flatten                        | Silver populada com fixtures           |
| 9    | Agent Processing + restante das Skills de Processing       | Todas tabelas Silver populadas         |
| 10   | dbt: sources + staging models + testes básicos             | `dbt run` + `dbt test` passando       |
| 11   | dbt: intermediate models (team_form, elo, h2h, odds)       | Features calculadas corretamente       |
| 12   | dbt: mart models (fct_match_features principal)            | Feature matrix completa                |
| 13   | Docker: MLflow                                              | http://localhost:5000 — UI OK          |
| 14   | Skills ML: training + evaluation + registry                | Modelo treinado e registrado           |
| 15   | Skills ML: prediction_generator + writer                   | Predições na Gold                      |
| 16   | PostgreSQL: tabelas football serving (init script)         | Tabelas criadas                        |
| 17   | Skills Serving: upsert + cache invalidator                 | Dados no PostgreSQL serving            |
| 18   | Skills Quality: todos os checks                            | Quality agent executa sem falha        |
| 19   | DAG: football_daily_pipeline completa                      | Pipeline end-to-end funcional          |
| 20   | Docker: FastAPI                                             | http://localhost:8000/health OK        |
| 21   | API: routers + services + schemas                          | GET /predictions/{id} retorna dados    |
| 22   | DAGs restantes: matchday, weekly_retrain, maintenance      | Todas DAGs testadas                    |
| 23   | dbt: unit tests + singular tests completos                 | 100% testes passando                   |
| 24   | dbt: docs + lineage                                        | http://localhost:8001 — lineage OK     |
| 25   | Testes: integração e2e                                     | Pipeline completo testado              |
| 26   | Documentação: runbook, data dictionary, ADRs               | Documentação revisada                  |

---

## 22. Resumo de Portas

| Serviço            | Porta | URL                           |
|--------------------|-------|-------------------------------|
| PostgreSQL Airflow | 5432  | postgres-airflow:5432         |
| PostgreSQL Serving | 5433  | postgres-serving:5432         |
| Redis              | 6379  | redis:6379                    |
| Airflow Webserver  | 8080  | http://localhost:8080          |
| Airflow Flower     | 5555  | http://localhost:5555          |
| Spark Master UI    | 8081  | http://localhost:8081          |
| MLflow UI          | 5000  | http://localhost:5000          |
| FastAPI            | 8000  | http://localhost:8000          |
| dbt docs           | 8001  | http://localhost:8001          |

---

## 23. Resumo de Credenciais Iniciais

| Serviço            | Usuário | Senha | Trocar? |
|--------------------|---------|-------|---------|
| PostgreSQL Airflow | admin   | admin | SIM     |
| PostgreSQL Serving | admin   | admin | SIM     |
| Redis              | —       | admin | SIM     |
| Airflow            | admin   | admin | SIM     |
| MLflow             | —       | —     | —       |

---

> **Este documento mapeia cada arquivo a ser implementado no Football Prediction Engine.**
> A ordem de implementação (seção 21) é o caminho crítico — seguir na sequência.
> Cada arquivo referencia o PRD Football como fonte de verdade arquitetural.
> Código é consequência da arquitetura — este mapa garante que nada seja esquecido.
