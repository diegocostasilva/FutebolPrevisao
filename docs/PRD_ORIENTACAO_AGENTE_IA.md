# PRD — MCP Agent DAG Platform

## Documento de Orientação para Agente de IA

| Campo              | Valor                                                          |
|--------------------|----------------------------------------------------------------|
| Versão             | 2.0.0                                                          |
| Data               | 2026-03-29                                                     |
| Classificação      | Referência Arquitetural — Agente de IA                         |
| Stack              | MCP · Airflow · Databricks · PostgreSQL · dbt                  |
| Propósito          | Guia de decisão e orientação para assistente de IA             |

---

## 1. Propósito deste Documento

Este documento é a **fonte de verdade arquitetural** que o agente de IA deve consultar ao auxiliar no desenvolvimento, manutenção e evolução da plataforma de dados. Ele não contém código — contém **princípios, decisões, restrições e padrões** que orientam toda ação técnica.

Toda recomendação, geração de código ou análise feita pelo agente deve respeitar as definições aqui estabelecidas.

---

## 2. Visão da Plataforma

A **MCP Agent DAG Platform** é uma plataforma de engenharia de dados de produção que opera em quatro camadas fundamentais:

- **Orquestração** → Apache Airflow controla quando e em que ordem as coisas acontecem.
- **Inteligência de Execução** → Agents decidem como executar, com retry e tratamento de erro.
- **Capacidade Técnica** → MCP Skills são as unidades atômicas de trabalho real.
- **Governança e Transformação** → dbt + Databricks + PostgreSQL garantem qualidade, lineage e servimento.

O diferencial desta arquitetura é que **o Airflow nunca executa lógica de negócio diretamente**. Ele dispara Agents, que por sua vez orquestram Skills. Essa separação de responsabilidades é inegociável.

---

## 3. Diagrama Conceitual

```
╔═══════════════════════════════════════════════════════════════╗
║                        ORQUESTRAÇÃO                          ║
║                     Apache Airflow (DAG)                     ║
║                                                               ║
║   Responsabilidade: QUANDO e EM QUE ORDEM executar            ║
║   Não contém: lógica de negócio, transformação, conexões      ║
╠═══════════════════════════════════════════════════════════════╣
║                        AGENTS                                 ║
║              Ingestion · Processing · dbt · Serving           ║
║                                                               ║
║   Responsabilidade: COMO executar (retry, rollback, logging)  ║
║   Agrupa Skills, decide sequência, trata erros                ║
╠═══════════════════════════════════════════════════════════════╣
║                       MCP SKILLS                              ║
║   API Extractor · Spark Transform · dbt Run · PG Upsert      ║
║   Row Count Check · Schema Drift · Slack Notifier · ...       ║
║                                                               ║
║   Responsabilidade: O QUÊ fazer (unidade atômica de trabalho) ║
║   Stateless · Contrato único · Testável isoladamente          ║
╠═══════════════════════════════════════════════════════════════╣
║                    INFRAESTRUTURA                             ║
║                                                               ║
║   Databricks (Spark/Delta)  ·  PostgreSQL  ·  Redis  ·  dbt  ║
║                                                               ║
║   Responsabilidade: ONDE os dados vivem e são transformados   ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## 4. Fluxo de Dados — Visão Macro

```
Fontes Externas                Databricks                      Consumo
(APIs, JDBC, S3, CSV)         (Spark + Delta Lake)            (BI, API, App)
                                                               
      │                             │                             ▲
      ▼                             │                             │
┌───────────┐              ┌────────▼────────┐           ┌───────┴───────┐
│ INGESTION │              │     BRONZE      │           │  POSTGRESQL   │
│   AGENT   │─────────────▶│   (Raw Data)    │           │ Serving Layer │
└───────────┘              └────────┬────────┘           └───────▲───────┘
                                    │                             │
                           ┌────────▼────────┐           ┌───────┴───────┐
                           │     SILVER      │           │   SERVING     │
                           │  (Clean Data)   │           │    AGENT      │
                           └────────┬────────┘           └───────▲───────┘
                                    │                             │
                           ┌────────▼────────┐           ┌───────┴───────┐
                           │      GOLD       │           │   dbt AGENT   │
                           │   (Mart Data)   │◀──────────│ (Transformação│
                           └─────────────────┘           │   Analítica)  │
                                                         └───────────────┘
```

A leitura correta deste fluxo é: os dados entram pela esquerda, são processados no centro (Databricks), transformados pelo dbt, e servidos à direita (PostgreSQL). Cada transição entre camadas é responsabilidade de um Agent específico.

---

## 5. Princípios Arquiteturais

Estes são os princípios que **nunca devem ser violados**. O agente de IA deve validar toda recomendação contra esta lista.

### 5.1 Separação de Responsabilidades

O Airflow orquestra. Os Agents decidem. As Skills executam. Misturar essas responsabilidades gera acoplamento, dificulta testes e compromete manutenibilidade. Uma DAG do Airflow deve conter apenas chamadas a Agents — nunca lógica de transformação, queries SQL ou chamadas diretas a APIs.

### 5.2 Skills são Stateless

Uma MCP Skill não mantém estado entre execuções. Ela recebe um Context, executa sua tarefa e retorna um Result. Toda informação necessária vem no Context. Isso garante que qualquer Skill pode ser testada isoladamente, reexecutada sem efeitos colaterais e substituída sem impacto no restante do pipeline.

### 5.3 Context é o Contrato Universal

O objeto Context é o único mecanismo de comunicação entre camadas. Ele carrega identificação da execução (run_id, dag_id, task_id), conexões, parâmetros dinâmicos e artefatos produzidos por Skills anteriores. Nenhuma Skill deve buscar configuração fora do Context.

### 5.4 Fail-Fast com Rollback

Quando uma Skill falha, o Agent deve interromper a execução imediatamente, invocar o rollback da Skill que falhou (quando disponível) e propagar o erro. Continuar executando Skills subsequentes após uma falha gera dados inconsistentes e dificulta diagnóstico.

### 5.5 Dados são Imutáveis por Camada

Na Bronze, os dados nunca são alterados após a ingestão — apenas novos registros são adicionados. Na Silver, atualizações são feitas via MERGE (upsert), preservando histórico. Na Gold, tabelas são reconstruídas ou atualizadas de forma idempotente. Essa imutabilidade por camada garante auditabilidade e reprocessamento seguro.

### 5.6 Infraestrutura como Containers Isolados

Cada ferramenta open source opera em seu próprio Docker Compose, conectada às demais via uma rede bridge compartilhada (mcp_network). Isso permite escalar, substituir ou atualizar qualquer componente sem afetar os demais.

---

## 6. Componentes da Arquitetura

### 6.1 Apache Airflow

**Papel**: Orquestrador de workflows. Define a sequência e o agendamento dos Agents.

**O que o Airflow FAZ nesta plataforma:**

- Define a ordem de execução dos Agents via DAGs.
- Controla agendamento (diário, horário, semanal).
- Gerencia retry, timeout e SLA.
- Armazena logs de execução.
- Envia alertas em caso de falha.

**O que o Airflow NÃO FAZ nesta plataforma:**

- Não executa transformações de dados.
- Não faz queries SQL diretamente.
- Não chama APIs de terceiros diretamente.
- Não armazena lógica de negócio.

**Decisões arquiteturais:**

- Executor: CeleryExecutor com Redis como broker, permitindo escalar workers.
- Metadata: PostgreSQL dedicado (instância separada do serving).
- Timezone: America/Sao_Paulo.
- Padrão de DAG: sempre `catchup=False`, `max_active_runs=1` para pipelines diários, `execution_timeout` e `sla` obrigatórios.

**Docker**: container próprio com Webserver, Scheduler, Worker e Flower (monitor Celery), todos na mcp_network.

### 6.2 Databricks (Spark + Delta Lake)

**Papel**: Processamento distribuído e armazenamento em formato Delta Lake, organizado em Medallion Architecture.

**Camadas Medallion:**

| Camada  | Propósito                        | Materialização | Retenção         |
|---------|----------------------------------|----------------|------------------|
| Bronze  | Dados brutos, schema-on-read     | Append-only    | 30 dias de log   |
| Silver  | Dados limpos, tipados, deduplicados | MERGE (upsert) | 60 dias de log |
| Gold    | Agregações e marts de negócio    | Overwrite/Merge | 90 dias de log  |

**Regras de Particionamento:**

- `PARTITION BY` deve ser usado exclusivamente em colunas de **baixa cardinalidade** usadas em filtros de range. Na prática, isso significa datas (ingestion_date, event_date, metric_date). Nunca particionar por IDs, nomes ou campos de texto livre.
- O objetivo do particionamento é que cada partição contenha entre 256 MB e 1 GB de dados. Partições menores que 128 MB indicam over-partitioning.

**Regras de ZORDER:**

- `ZORDER BY` deve ser usado em colunas de **alta cardinalidade** frequentemente usadas em filtros pontuais (WHERE, JOIN). Exemplos: user_id, event_type, region, product_category.
- Nunca usar mais de 4 colunas no ZORDER — o retorno marginal é decrescente e o custo de OPTIMIZE aumenta.
- ZORDER é executado via `OPTIMIZE` e deve ser agendado como job de manutenção (semanal) ou no `post_hook` do dbt.

**Tabela de referência — Particionamento e ZORDER por camada:**

| Camada  | Tabela Exemplo      | PARTITION BY      | ZORDER BY                    |
|---------|---------------------|-------------------|------------------------------|
| Bronze  | raw_events          | _ingestion_date   | source_system, event_type    |
| Silver  | events              | event_date        | user_id, event_type          |
| Silver  | users               | —                 | user_id, region              |
| Gold    | fct_daily_metrics   | metric_date       | region, product_category     |
| Gold    | fct_monthly_summary | —                 | region                       |

**Manutenção obrigatória:**

- OPTIMIZE + ZORDER: semanal, em horário de baixa carga.
- VACUUM: semanal, com retenção mínima de 168 horas (Bronze/Silver) e 720 horas (Gold).
- ANALYZE: após OPTIMIZE, para atualizar estatísticas do query optimizer.

**Propriedades Delta obrigatórias em toda tabela:**

- `delta.autoOptimize.optimizeWrite = true`
- `delta.autoOptimize.autoCompact = true`
- Tag `quality` indicando a camada (bronze, silver, gold).

**Governança**: Unity Catalog habilitado. Catálogo único `mcp_platform` com schemas por camada.

### 6.3 dbt (Data Build Tool)

**Papel**: Transformação analítica SQL dentro do Databricks, com testes, documentação e lineage.

**Camadas no dbt:**

| Camada dbt     | Materialização | Schema Databricks | Propósito                              |
|----------------|----------------|-------------------|----------------------------------------|
| staging        | view           | staging           | Renomeação, tipagem, filtros básicos   |
| intermediate   | ephemeral      | —                 | Joins e enriquecimentos intermediários |
| mart           | table (Delta)  | gold              | Agregações finais para consumo         |

**Padrões obrigatórios:**

- Staging models leem de sources (Silver), nunca de Bronze diretamente.
- Intermediate models são ephemeral — não geram tabelas físicas, apenas CTEs reutilizáveis.
- Mart models produzem tabelas Delta com `PARTITION BY` e `OPTIMIZE + ZORDER` via post_hook.
- Todo modelo de mart deve ter schema tests definidos (not_null, unique, accepted_values, range checks).
- Snapshots para dimensões que mudam ao longo do tempo (SCD Tipo 2).

**Testes — Estratégia de Três Níveis:**

| Nível            | O que testa                              | Quando executa          |
|------------------|------------------------------------------|-------------------------|
| Unit Tests       | Lógica de transformação com dados mock   | A cada PR / commit      |
| Schema Tests     | Integridade dos dados (null, unique, range) | Após cada `dbt run`  |
| Singular Tests   | Regras de negócio específicas            | Após cada `dbt run`     |

- Unit tests usam o framework nativo do dbt 1.8+ com `given` (inputs mock) e `expect` (outputs esperados).
- Schema tests são declarados nos YAML de cada modelo usando `dbt_expectations` para validações avançadas.
- Singular tests são queries SQL que retornam linhas com problema — se retornar qualquer linha, o teste falha.

**Lineage e Documentação:**

- `dbt docs generate` produz o grafo de lineage completo da plataforma.
- `dbt docs serve` expõe a documentação na porta 8001.
- Todo modelo de mart deve ter um bloco `{% docs %}` explicando granularidade, lineage resumido, particionamento e frequência de refresh.
- O lineage do dbt é a referência oficial para entender dependências entre modelos.

### 6.4 PostgreSQL

**Papel**: Duas instâncias isoladas com funções distintas.

| Instância         | Porta | Função                                | Schemas                    |
|--------------------|-------|---------------------------------------|----------------------------|
| postgres-airflow   | 5432  | Metadata do Airflow + Celery backend  | Gerenciado pelo Airflow    |
| postgres-serving   | 5433  | Serving layer para BI, APIs e apps    | staging, serving, audit, cache |

**Regras para o Serving Layer:**

- Schema `serving` contém apenas dados prontos para consumo. Nunca dados intermediários.
- Schema `audit` registra toda execução de pipeline (run_id, agent, skill, status, rows_affected, duração).
- Schema `staging` é área temporária para cargas incrementais antes do upsert final.
- Schema `cache` armazena materialized views para dashboards de alta frequência.
- Toda tabela de serving deve ter índices nos campos de filtro mais usados.
- Materialized Views para agregações pesadas, com refresh agendado.
- Connection pooling (PgBouncer) obrigatório em produção.

### 6.5 Redis

**Papel**: Broker de mensagens para o CeleryExecutor do Airflow e cache de sessão.

- Configurado com `maxmemory-policy allkeys-lru` para evitar estouro de memória.
- Persistência via append-only file (AOF) habilitada.
- Não armazena dados de negócio — apenas filas de tasks e resultados do Celery.

### 6.6 Spark Standalone (Local)

**Papel**: Ambiente de desenvolvimento e teste local, espelhando o comportamento do Databricks.

- Master + Worker em containers separados.
- Usado para validar transformações PySpark antes de enviar ao Databricks.
- Não é usado em produção — produção roda exclusivamente no Databricks.

---

## 7. Modelo de Agents e Skills

### 7.1 Taxonomia de Agents

| Agent              | Responsabilidade                                         | Skills que utiliza                         |
|--------------------|----------------------------------------------------------|--------------------------------------------|
| Ingestion Agent    | Coleta dados das fontes e grava na Bronze                | API Extractor, JDBC Extractor, S3 Extractor, CSV Extractor |
| Processing Agent   | Transforma Bronze → Silver (limpeza, dedup, tipagem)     | Spark Bronze→Silver, Schema Enforcer, Row Count Check |
| dbt Agent          | Executa modelos dbt (staging → mart) + testes            | dbt Run, dbt Test, dbt Docs              |
| Serving Agent      | Carrega dados Gold no PostgreSQL serving                 | PG Upsert, PG Loader, Cache Invalidator  |
| Quality Agent      | Valida qualidade pós-pipeline                            | Row Count, Null Check, Freshness Check, Schema Drift |
| Notification Agent | Envia alertas sobre sucesso, falha ou divergência        | Slack Notifier, Email Notifier, PagerDuty |

### 7.2 Contrato de uma MCP Skill

Toda Skill deve implementar:

| Método       | Obrigatório | Descrição                                              |
|--------------|-------------|--------------------------------------------------------|
| name         | Sim         | Identificador único da Skill (string)                  |
| version      | Sim         | Versionamento semântico (ex: 1.0.0)                   |
| validate     | Sim         | Verifica pré-condições antes de executar               |
| execute      | Sim         | Execução principal — recebe Context, retorna Result    |
| rollback     | Não         | Desfaz alterações em caso de falha                     |

**Regras de resultado (SkillResult):**

- `success`: booleano indicando se a execução foi bem-sucedida.
- `rows_affected`: quantidade de registros processados.
- `message`: descrição legível do resultado.
- `data`: dicionário opcional com metadados adicionais.
- `error`: exceção capturada, se houver.

### 7.3 Contrato de um Agent

| Comportamento      | Descrição                                                      |
|--------------------|----------------------------------------------------------------|
| Retry              | Configurável por Agent (padrão: 2 tentativas)                 |
| Fail-fast          | Interrompe execução na primeira Skill que falhar               |
| Rollback           | Invoca rollback da Skill que falhou                            |
| Logging            | Log estruturado por Skill executada (nome, versão, duração)    |
| Resultado          | Lista de SkillResults para rastreabilidade                     |

### 7.4 Fluxo de Execução — DAG → Agent → Skill

```
DAG (Airflow)
  │
  ├─ Task: ingestion_agent
  │    └─ Agent: IngestionAgent
  │         ├─ Skill: api_extractor        → validate → execute → result
  │         ├─ Skill: csv_extractor        → validate → execute → result
  │         └─ Skill: row_count_check      → validate → execute → result
  │
  ├─ Task: databricks_processing
  │    └─ DatabricksSubmitRunOperator (notebook Bronze → Silver)
  │
  ├─ Task: dbt_agent
  │    └─ Agent: DBTAgent
  │         ├─ Skill: dbt_run              → validate → execute → result
  │         └─ Skill: dbt_test             → validate → execute → result
  │
  ├─ Task: serving_agent
  │    └─ Agent: ServingAgent
  │         ├─ Skill: postgres_upsert      → validate → execute → result
  │         └─ Skill: cache_invalidator    → validate → execute → result
  │
  └─ Task: quality_agent
       └─ Agent: QualityAgent
            ├─ Skill: row_count_check      → validate → execute → result
            ├─ Skill: null_check           → validate → execute → result
            ├─ Skill: freshness_check      → validate → execute → result
            └─ Skill: schema_drift_check   → validate → execute → result
```

---

## 8. Infraestrutura Docker — Visão de Rede

### 8.1 Topologia

Cada ferramenta opera em seu próprio Docker Compose. Todos se conectam à rede bridge `mcp_network`, que é criada externamente antes de qualquer container subir.

```
┌─────────────────── mcp_network (bridge) ───────────────────┐
│                                                             │
│  ┌────────────────────┐    ┌────────────────────┐          │
│  │  docker-compose    │    │  docker-compose     │          │
│  │   .postgres.yml    │    │    .redis.yml       │          │
│  │                    │    │                     │          │
│  │ postgres-airflow   │    │  redis              │          │
│  │   :5432            │    │   :6379             │          │
│  │                    │    │                     │          │
│  │ postgres-serving   │    └────────────────────┘          │
│  │   :5433            │                                     │
│  └────────────────────┘    ┌────────────────────┐          │
│                            │  docker-compose     │          │
│  ┌────────────────────┐    │    .spark.yml       │          │
│  │  docker-compose    │    │                     │          │
│  │   .airflow.yml     │    │  spark-master       │          │
│  │                    │    │   :8081 / :7077     │          │
│  │ airflow-webserver  │    │                     │          │
│  │   :8080            │    │  spark-worker-1     │          │
│  │ airflow-scheduler  │    │                     │          │
│  │ airflow-worker-1   │    └────────────────────┘          │
│  │ airflow-flower     │                                     │
│  │   :5555            │                                     │
│  └────────────────────┘                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Comunicação entre Serviços

| De                  | Para               | Via                            | Propósito                    |
|---------------------|--------------------|--------------------------------|------------------------------|
| Airflow Scheduler   | PostgreSQL Airflow | postgres-airflow:5432          | Metadata e state             |
| Airflow Scheduler   | Redis              | redis:6379                     | Celery broker                |
| Airflow Worker      | PostgreSQL Airflow | postgres-airflow:5432          | Celery result backend        |
| Airflow Worker      | Databricks         | HTTPS (externo)                | Submit de jobs Spark         |
| Serving Agent       | PostgreSQL Serving | postgres-serving:5432          | Carga de dados Gold          |
| dbt                 | Databricks         | HTTPS (externo)                | Execução de modelos SQL      |
| Quality Agent       | PostgreSQL Serving | postgres-serving:5432          | Validação de dados           |

### 8.3 Credenciais Iniciais

Toda a stack sobe com credenciais `admin / admin`. Esta é uma decisão de design para simplificar o primeiro deploy. A troca de senhas é **obrigatória e imediata** após validar que a stack está funcional.

| Serviço            | Porta | Usuário | Senha | Interface                  |
|--------------------|-------|---------|-------|----------------------------|
| PostgreSQL Airflow | 5432  | admin   | admin | psql / DBeaver             |
| PostgreSQL Serving | 5433  | admin   | admin | psql / DBeaver             |
| Redis              | 6379  | —       | admin | redis-cli                  |
| Airflow            | 8080  | admin   | admin | http://localhost:8080      |
| Flower             | 5555  | —       | —     | http://localhost:5555      |
| Spark UI           | 8081  | —       | —     | http://localhost:8081      |
| dbt docs           | 8001  | —       | —     | http://localhost:8001      |

---

## 9. Ambiente Python

### 9.1 Especificação

- **Versão**: Python 3.12 (obrigatório — não usar 3.11 ou anterior).
- **Gerenciamento**: venv nativo (`python3.12 -m venv`).
- **Localização**: `/opt/mcp-platform/venv`.
- **Ativação**: `source /opt/mcp-platform/venv/bin/activate`.

### 9.2 Dependências por Domínio

| Domínio          | Pacotes Principais                                       |
|------------------|----------------------------------------------------------|
| Core             | pydantic, structlog, tenacity, python-dotenv, click      |
| Data             | psycopg2-binary, sqlalchemy, pandas, pyarrow             |
| Databricks       | databricks-sdk, databricks-sql-connector, pyspark, delta-spark |
| dbt              | dbt-core, dbt-databricks, dbt-postgres                  |
| HTTP             | requests, httpx                                          |
| Testes           | pytest, pytest-cov, pytest-mock                          |
| Qualidade        | ruff, mypy, pre-commit                                   |

### 9.3 Regra para o Agente

Ao gerar qualquer código Python para esta plataforma, o agente deve assumir que está rodando dentro do venv com todas essas dependências disponíveis. Imports devem ser diretos, sem instalações inline.

---

## 10. Boas Práticas — Guia de Decisão para o Agente

### 10.1 Quando o Agente criar uma MCP Skill

- A Skill deve ser stateless. Se precisar manter estado, o estado vai no Context.
- O método `validate` deve verificar TODAS as pré-condições antes de `execute` rodar.
- O retorno deve ser SEMPRE um SkillResult padronizado — nunca retornar dados soltos.
- Se a Skill altera dados (INSERT, UPDATE, DELETE), deve implementar `rollback`.
- O nome da Skill deve seguir o padrão `dominio_acao` (ex: `spark_bronze_to_silver`, `postgres_upsert`).
- A Skill deve ter versão semântica. Mudanças breaking incrementam o major.

### 10.2 Quando o Agente criar um Agent

- O Agent deve herdar de BaseAgent.
- As Skills devem ser declaradas em ordem de execução no construtor.
- O Agent não implementa lógica de negócio — ele apenas orquestra Skills.
- Retry deve ser configurável (padrão: 2 tentativas).
- Logging estruturado é obrigatório em cada Skill executada.

### 10.3 Quando o Agente criar uma DAG do Airflow

- Nunca colocar lógica de negócio dentro da DAG.
- Cada task deve chamar um Agent via PythonOperator, exceto para Databricks (usar DatabricksSubmitRunOperator).
- Obrigatório: `catchup=False`, `max_active_runs=1`, `execution_timeout`, `sla`, `retries`, `retry_delay`.
- Tags devem classificar a DAG (ex: `["mcp", "production", "daily"]`).
- Variáveis sensíveis devem vir de Airflow Variables ou Connections — nunca hardcoded.

### 10.4 Quando o Agente criar tabelas no Databricks

- Formato: sempre Delta Lake. Nunca Parquet puro, CSV ou JSON como tabelas gerenciadas.
- PARTITION BY: apenas colunas de data com baixa cardinalidade.
- ZORDER BY: colunas de alta cardinalidade usadas em filtros (máximo 4 colunas).
- Propriedades obrigatórias: `autoOptimize.optimizeWrite`, `autoOptimize.autoCompact`.
- Tag `quality` indicando camada (bronze, silver, gold).
- Catálogo: `mcp_platform`. Schemas: `bronze`, `silver`, `gold`.
- Metadados de carga (`_loaded_at`, `_batch_id`, `_ingestion_date`) obrigatórios em toda tabela.

### 10.5 Quando o Agente criar modelos dbt

- Staging: materializado como view, lê de sources Silver.
- Intermediate: materializado como ephemeral, nunca gera tabela física.
- Mart: materializado como table Delta, com PARTITION BY e ZORDER via post_hook.
- Todo modelo de mart deve ter schema tests no YAML correspondente.
- Unit tests para lógica de transformação complexa (agregações, cases, coalesces).
- Singular tests para regras de negócio que cruzam modelos (ex: orphan records).
- Documentação `{% docs %}` obrigatória para modelos de mart.

### 10.6 Quando o Agente trabalhar com PostgreSQL

- Serving layer: schema `serving` para dados prontos, `audit` para logs, `staging` para cargas temporárias.
- Upsert via `INSERT ON CONFLICT` — nunca DELETE + INSERT.
- Materialized Views para agregações consultadas frequentemente.
- Índices obrigatórios em colunas de filtro dos dashboards.
- Toda operação de carga deve registrar na tabela `audit.pipeline_execution`.

---

## 11. Observabilidade

### 11.1 Stack de Monitoramento

| Camada          | Ferramenta Recomendada         | Responsabilidade                    |
|-----------------|--------------------------------|-------------------------------------|
| Logs            | structlog → stdout/CloudWatch  | Logs estruturados JSON por Skill    |
| Métricas        | Prometheus + Grafana           | Duração, rows, taxa de erro         |
| Alertas         | Slack / PagerDuty via Skills   | Notificação de falha e divergência  |
| Data Quality    | Quality Agent + dbt tests      | Validação pós-pipeline              |
| Lineage         | dbt docs + OpenLineage         | Grafo de dependências               |
| Auditoria       | audit.pipeline_execution (PG)  | Registro de toda execução           |

### 11.2 O que deve ser logado

- Início e fim de cada Skill (com duração em ms).
- Quantidade de registros processados por Skill.
- Erros com stack trace completo.
- run_id e execution_date em toda linha de log (rastreabilidade).

---

## 12. Segurança e Governança

| Aspecto            | Implementação                                              |
|--------------------|------------------------------------------------------------|
| Secrets            | Airflow Connections + Secrets Manager (produção)           |
| RBAC               | Airflow RBAC + Databricks Unity Catalog                    |
| Encryption         | TLS em trânsito, AES-256 em repouso                       |
| Data Masking       | dbt macros para campos PII                                 |
| Audit Trail        | Log por Skill + run_id rastreável                          |
| Access Control     | PostgreSQL GRANT por schema + role (reader, writer)        |
| Credenciais        | admin/admin apenas para setup — troca imediata obrigatória |

---

## 13. Roadmap de Evolução

| Fase   | Escopo                                                    | Prioridade |
|--------|-----------------------------------------------------------|------------|
| v1.0   | Core: Skills + Agents + DAG + Databricks + PG + dbt      | Atual      |
| v1.1   | Quality Agent com dbt tests + Great Expectations          | Alta       |
| v1.2   | MLflow: ML Agent + Feature Store Skills                   | Média      |
| v2.0   | Streaming: Kafka Agent + Spark Structured Streaming       | Média      |
| v2.1   | API Layer: FastAPI serving + GraphQL                      | Baixa      |
| v3.0   | Multi-cloud: Terraform para AWS / Azure / GCP             | Futura     |

---

## 14. Glossário

| Termo              | Definição                                                               |
|--------------------|-------------------------------------------------------------------------|
| MCP                | Model Context Protocol — padrão de modularização de Skills              |
| Skill              | Unidade atômica de execução, stateless, com contrato definido           |
| Agent              | Orquestrador de Skills com retry, rollback e logging                    |
| DAG                | Directed Acyclic Graph — grafo de dependências no Airflow               |
| Medallion          | Arquitetura de camadas: Bronze → Silver → Gold                          |
| Serving Layer      | Camada PostgreSQL com dados prontos para consumo                        |
| Context            | Objeto que carrega configuração, conexões e estado da execução          |
| SkillResult        | Objeto padronizado retornado por toda Skill                             |
| Delta Lake         | Formato de armazenamento ACID no Databricks                            |
| Unity Catalog      | Governança centralizada de dados no Databricks                         |
| ZORDER             | Co-localização de dados em arquivos Delta para acelerar queries         |
| OPTIMIZE           | Compactação de small files em Delta Lake                                |
| VACUUM             | Remoção de arquivos antigos não referenciados em Delta                  |
| SCD Tipo 2         | Slowly Changing Dimension — preserva histórico de alterações            |
| Ephemeral          | Materialização dbt que não gera tabela física (apenas CTE)              |
| post_hook          | Comando SQL executado automaticamente após materialização dbt           |

---

## 15. Referências Oficiais

| Tecnologia        | Documentação                                      |
|-------------------|---------------------------------------------------|
| Apache Airflow    | https://airflow.apache.org/docs/                  |
| Databricks        | https://docs.databricks.com/                      |
| Delta Lake        | https://docs.delta.io/                            |
| OPTIMIZE + ZORDER | https://docs.databricks.com/delta/optimize.html   |
| Unity Catalog     | https://docs.databricks.com/data-governance/      |
| dbt Core          | https://docs.getdbt.com/                          |
| dbt Unit Tests    | https://docs.getdbt.com/docs/build/unit-tests     |
| dbt-databricks    | https://github.com/databricks/dbt-databricks      |
| PostgreSQL 16     | https://www.postgresql.org/docs/16/               |
| MCP Specification | https://modelcontextprotocol.io/                  |
| OpenLineage       | https://openlineage.io/                           |
| Docker Compose    | https://docs.docker.com/compose/compose-file/     |

---

> **Este documento é a referência arquitetural da MCP Agent DAG Platform.**
> O agente de IA deve consultar este documento antes de qualquer decisão técnica.
> Toda implementação deve estar alinhada com os princípios e padrões aqui definidos.
> Código é consequência da arquitetura — nunca o contrário.
