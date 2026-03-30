# PRD — Football Prediction Engine

## Extensão da MCP Agent DAG Platform

| Campo              | Valor                                                          |
|--------------------|----------------------------------------------------------------|
| Versão             | 1.0.0                                                          |
| Data               | 2026-03-29                                                     |
| Classificação      | Referência Arquitetural — Agente de IA                         |
| Domínio            | Sports Analytics · Football Prediction                         |
| Fonte de Dados     | API-Football (api-football.com) v3                             |
| Base               | PRD_ORIENTACAO_AGENTE_IA.md (documento pai)                    |
| Status             | Draft → Review → Aprovado                                      |

---

## 1. Propósito

Este documento é a extensão oficial da MCP Agent DAG Platform para o domínio de **predição de resultados de futebol**. Ele define a arquitetura, os componentes, os fluxos de dados e as regras que o agente de IA deve seguir ao trabalhar com este domínio.

Este documento **herda todos os princípios** do PRD pai (separação de responsabilidades, Skills stateless, Context como contrato, fail-fast, Medallion, etc.) e os **especializa** para o contexto de futebol.

Nenhuma definição aqui contradiz o PRD pai. Em caso de dúvida, o PRD pai prevalece.

---

## 2. Visão do Produto

O **Football Prediction Engine** é um sistema de predição de resultados de futebol que opera como um domínio dentro da plataforma MCP existente. Ele coleta dados de partidas, estatísticas, odds e jogadores via API-Football, processa através da arquitetura Medallion no Databricks, transforma via dbt, treina modelos de ML, e serve previsões via PostgreSQL e API REST.

O objetivo final é gerar, para cada partida futura, três probabilidades: vitória do mandante, empate e vitória do visitante — com modelo versionado, rastreável e continuamente retreinado.

---

## 3. Diagrama de Visão — Fluxo Completo

```
                          API-FOOTBALL (v3)
                    ┌─────────────────────────────┐
                    │  /fixtures                   │
                    │  /fixtures/statistics         │
                    │  /fixtures/events             │
                    │  /fixtures/lineups            │
                    │  /fixtures/players            │
                    │  /odds                        │
                    │  /odds/live                   │
                    │  /predictions                 │
                    │  /teams/statistics            │
                    │  /players                     │
                    │  /standings                   │
                    │  /leagues                     │
                    │  /injuries                    │
                    │  /coaches                     │
                    │  /transfers                   │
                    └──────────┬──────────────────┘
                               │
                               ▼
╔══════════════════════════════════════════════════════════════════╗
║                    AIRFLOW — DAG: football_pipeline              ║
║                                                                  ║
║  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌───────────┐ ║
║  │Ingestion │→│Processing│→│  dbt   │→│   ML   │→│  Serving  │ ║
║  │  Agent   │ │  Agent   │ │ Agent  │ │ Agent  │ │   Agent   │ ║
║  └──────────┘ └──────────┘ └────────┘ └────────┘ └───────────┘ ║
╚══════════════════════════════════════════════════════════════════╝
       │              │            │          │            │
       ▼              ▼            ▼          ▼            ▼
  ┌─────────┐   ┌──────────┐  ┌────────┐ ┌────────┐ ┌──────────┐
  │ BRONZE  │   │  SILVER  │  │  GOLD  │ │ MLflow │ │PostgreSQL│
  │(Delta)  │   │ (Delta)  │  │(Delta) │ │Registry│ │ Serving  │
  │         │   │          │  │        │ │        │ │          │
  │raw JSON │   │flatten + │  │features│ │modelos │ │previsões │
  │append   │   │dedup     │  │+ marts │ │treinados││+ métricas│
  └─────────┘   └──────────┘  └────────┘ └────────┘ └────┬─────┘
                                                          │
                                                          ▼
                                                    ┌──────────┐
                                                    │ FastAPI   │
                                                    │ /predict  │
                                                    │ /fixtures │
                                                    │ /standings│
                                                    └──────────┘
```

---

## 4. Fonte de Dados — API-Football v3

### 4.1 Visão Geral

A API-Football é uma API REST que cobre mais de 1.200 ligas e copas com dados em tempo real. O acesso é feito via chave de API obtida no dashboard (dashboard.api-football.com). A API retorna JSON em todas as respostas.

Base URL: `https://v3.football.api-sports.io`

Autenticação: header `x-apisports-key` com a chave do plano contratado.

### 4.2 Endpoints Relevantes para o Domínio

O sistema consome 14 endpoints organizados em 4 grupos funcionais.

**Grupo 1 — Estrutura e Referência**

Estes endpoints fornecem dados estruturais que mudam raramente. Devem ser coletados na inicialização e atualizados semanalmente.

| Endpoint         | Propósito                                      | Frequência de Coleta |
|------------------|-------------------------------------------------|----------------------|
| `/leagues`       | Lista de ligas e copas com cobertura disponível | Semanal              |
| `/teams`         | Informações de times (nome, logo, venue)        | Semanal              |
| `/players`       | Dados de jogadores (posição, idade, stats)      | Semanal              |
| `/coaches`       | Técnicos e histórico de carreira                | Semanal              |
| `/standings`     | Classificação atualizada por liga/season         | Diária               |
| `/injuries`      | Jogadores lesionados ou suspensos               | Diária (dia de jogo) |
| `/transfers`     | Transferências de jogadores                     | Semanal              |

**Grupo 2 — Partidas e Eventos**

Estes são os endpoints centrais do pipeline. Fornecem dados de partidas passadas, ao vivo e futuras.

| Endpoint                | Propósito                                    | Frequência de Coleta     |
|-------------------------|----------------------------------------------|--------------------------|
| `/fixtures`             | Lista de partidas (passadas, live, futuras)  | Diária (backfill + incremental) |
| `/fixtures/statistics`  | Estatísticas por time em cada partida        | Após conclusão da partida |
| `/fixtures/events`      | Eventos (gols, cartões, substituições)       | Após conclusão da partida |
| `/fixtures/lineups`     | Escalações titulares e reservas              | Dia do jogo              |
| `/fixtures/players`     | Estatísticas individuais por jogador/partida | Após conclusão da partida |

**Grupo 3 — Odds e Mercados**

Dados de casas de apostas. Fundamentais para features do modelo de predição.

| Endpoint       | Propósito                                  | Frequência de Coleta      |
|----------------|--------------------------------------------|---------------------------|
| `/odds`        | Odds pré-jogo por bookmaker e mercado      | Diária (pré-jogo)         |
| `/odds/live`   | Odds ao vivo durante partida               | Tempo real (se aplicável) |

**Grupo 4 — Predições da Própria API**

A API-Football oferece predições próprias calculadas por 6 algoritmos internos. Devem ser coletadas como feature adicional, não como substituto do modelo próprio.

| Endpoint         | Propósito                                     | Frequência de Coleta |
|------------------|------------------------------------------------|----------------------|
| `/predictions`   | Predição da API (winner, under/over, H2H)     | Dia do jogo          |

### 4.3 Ligas Prioritárias — Brasileirão Focus

O sistema deve priorizar a cobertura do futebol brasileiro, expandindo para outras ligas conforme necessidade.

| Prioridade | Liga                        | ID API-Football | Country |
|------------|-----------------------------|-----------------|---------|
| P0         | Brasileirão Série A         | 71              | Brazil  |
| P0         | Brasileirão Série B         | 72              | Brazil  |
| P1         | Copa do Brasil              | 73              | Brazil  |
| P1         | Copa Libertadores           | 13              | World   |
| P1         | Copa Sul-Americana          | 11              | World   |
| P2         | Premier League              | 39              | England |
| P2         | La Liga                     | 140             | Spain   |
| P2         | Serie A (Itália)            | 135             | Italy   |
| P2         | Champions League            | 2               | World   |
| P3         | Bundesliga                  | 78              | Germany |
| P3         | Ligue 1                     | 61              | France  |
| P3         | Copa do Mundo               | 1               | World   |

**Regra para o agente**: toda implementação deve funcionar primeiro com Brasileirão Série A (P0) antes de expandir para outras ligas. O ID 71 é a referência de desenvolvimento.

### 4.4 Gestão de Quota da API

| Plano    | Requests/dia | Requests/min | Seasons Disponíveis |
|----------|-------------|--------------|---------------------|
| Free     | 100         | 30           | Season atual        |
| Pro      | 7.500       | 300          | Todas               |
| Ultra    | 150.000     | 450          | Todas               |
| Mega     | 500.000     | 450          | Todas               |

**Regras de gestão de quota que o agente deve seguir:**

- Antes de implementar qualquer extração, verificar a cobertura da liga via campo `coverage` do endpoint `/leagues`.
- Usar o endpoint `/fixtures?ids=ID1-ID2-...-ID20` para buscar até 20 partidas por request (incluindo events, lineups, statistics e players).
- Implementar rate limiting na Skill de extração respeitando o limite por minuto do plano.
- Armazenar dados brutos na Bronze para evitar re-chamadas. Nunca chamar a API para dados já coletados.
- Implementar incremental extraction por data — só buscar partidas novas ou atualizadas.
- Registrar cada chamada à API no log de auditoria com: endpoint, parâmetros, status HTTP, requests restantes no header de resposta.

---

## 5. Arquitetura Medallion — Modelo de Dados Football

### 5.1 Visão por Camada

```
╔═══════════════════════════════════════════════════════════════╗
║                          BRONZE                               ║
║         Catálogo: mcp_platform  ·  Schema: bronze             ║
║                                                               ║
║  Dados brutos da API-Football em JSON.                        ║
║  Append-only. Nunca alterados após ingestão.                  ║
║  Uma tabela por endpoint.                                     ║
║                                                               ║
║  football_fixtures_raw                                        ║
║  football_statistics_raw                                      ║
║  football_events_raw                                          ║
║  football_lineups_raw                                         ║
║  football_players_stats_raw                                   ║
║  football_odds_raw                                            ║
║  football_odds_live_raw                                       ║
║  football_predictions_raw                                     ║
║  football_standings_raw                                       ║
║  football_teams_raw                                           ║
║  football_players_raw                                         ║
║  football_injuries_raw                                        ║
║  football_coaches_raw                                         ║
║  football_transfers_raw                                       ║
║  football_leagues_raw                                         ║
╚═══════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════╗
║                          SILVER                               ║
║         Catálogo: mcp_platform  ·  Schema: silver             ║
║                                                               ║
║  JSON flattened. Tipagem correta. Deduplicado. Normalizado.   ║
║  Chaves compostas e surrogate keys criadas.                   ║
║  Uma tabela por entidade de negócio.                          ║
║                                                               ║
║  Entidades de Partida:                                        ║
║    football_fixtures         (partida com resultado)          ║
║    football_match_statistics (stats por time por partida)     ║
║    football_match_events     (gols, cartões, substituições)   ║
║    football_match_lineups    (escalações por partida)         ║
║    football_player_match_stats (stats por jogador por jogo)  ║
║                                                               ║
║  Entidades de Odds:                                           ║
║    football_odds_prematch    (odds pré-jogo por bookmaker)   ║
║    football_odds_live        (odds ao vivo)                   ║
║                                                               ║
║  Entidades de Referência:                                     ║
║    football_leagues          (ligas e copas)                  ║
║    football_teams            (times)                          ║
║    football_players          (jogadores)                      ║
║    football_coaches          (técnicos)                       ║
║    football_standings        (classificação)                  ║
║    football_injuries         (lesões e suspensões)            ║
║    football_transfers        (transferências)                 ║
║    football_api_predictions  (predições da própria API)       ║
╚═══════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════╗
║                           GOLD                                ║
║         Catálogo: mcp_platform  ·  Schema: gold               ║
║         Transformado via dbt (staging → intermediate → mart)  ║
║                                                               ║
║  Feature Store (input para ML):                               ║
║    fct_match_features        (feature matrix para treino)     ║
║    fct_team_form             (forma recente por time)         ║
║    fct_team_strength         (rating ELO por time)            ║
║    fct_head_to_head          (histórico confrontos diretos)   ║
║    fct_player_impact         (impacto estatístico jogadores)  ║
║    fct_odds_consensus        (odds consolidadas por partida)  ║
║                                                               ║
║  Marts Analíticos:                                            ║
║    fct_league_summary        (resumo por rodada/liga)         ║
║    fct_team_season_stats     (stats acumuladas por temporada) ║
║    dim_teams                 (dimensão times enriquecida)     ║
║    dim_leagues               (dimensão ligas)                 ║
║    dim_players               (dimensão jogadores)             ║
║                                                               ║
║  Predições (output do ML):                                    ║
║    fct_match_predictions     (probabilidades geradas)         ║
║    fct_model_performance     (métricas de acurácia)           ║
╚═══════════════════════════════════════════════════════════════╝
```

### 5.2 Chaves Primárias e Relacionamentos

O modelo de dados se organiza ao redor de 5 chaves naturais que vêm da API-Football.

| Chave         | Origem              | Tipo   | Escopo                     |
|---------------|----------------------|--------|----------------------------|
| fixture_id    | API-Football         | INT    | Identificador único de partida — persistente entre endpoints |
| team_id       | API-Football         | INT    | Identificador de time — persistente entre competições |
| league_id     | API-Football         | INT    | Identificador de liga/copa   |
| player_id     | API-Football         | INT    | Identificador de jogador     |
| season        | API-Football         | INT    | Ano da temporada (ex: 2025 para 2025/2026) |

**Regra para o agente**: `fixture_id` é a chave universal de partida. Todo dado de estatística, evento, lineup, odds ou predição se conecta a uma partida via `fixture_id`. Ao modelar qualquer entidade, o `fixture_id` deve ser a referência principal.

**Relacionamentos:**

```
leagues (league_id)
    │
    ├── standings (league_id + season)
    │
    └── fixtures (fixture_id)
            │
            ├── match_statistics (fixture_id + team_id)
            ├── match_events (fixture_id)
            ├── match_lineups (fixture_id + team_id)
            ├── player_match_stats (fixture_id + player_id)
            ├── odds_prematch (fixture_id + bookmaker)
            └── predictions (fixture_id)

teams (team_id)
    │
    ├── players (player_id + team_id + season)
    ├── coaches (team_id)
    ├── injuries (team_id + player_id)
    └── transfers (team_id + player_id)
```

### 5.3 Particionamento e ZORDER — Tabela de Referência

**Bronze:**

| Tabela                       | PARTITION BY       | ZORDER BY                     |
|------------------------------|--------------------|-------------------------------|
| football_fixtures_raw        | _ingestion_date    | league_id                     |
| football_statistics_raw      | _ingestion_date    | fixture_id                    |
| football_events_raw          | _ingestion_date    | fixture_id                    |
| football_lineups_raw         | _ingestion_date    | fixture_id                    |
| football_players_stats_raw   | _ingestion_date    | fixture_id                    |
| football_odds_raw            | _ingestion_date    | fixture_id                    |
| football_standings_raw       | _ingestion_date    | league_id                     |
| football_teams_raw           | _ingestion_date    | —                             |
| football_players_raw         | _ingestion_date    | team_id                       |
| football_injuries_raw        | _ingestion_date    | team_id                       |
| football_leagues_raw         | _ingestion_date    | —                             |

**Silver:**

| Tabela                        | PARTITION BY    | ZORDER BY                      |
|-------------------------------|-----------------|--------------------------------|
| football_fixtures             | match_date      | fixture_id, league_id          |
| football_match_statistics     | match_date      | fixture_id, team_id            |
| football_match_events         | match_date      | fixture_id, event_type         |
| football_match_lineups        | match_date      | fixture_id, team_id            |
| football_player_match_stats   | match_date      | fixture_id, player_id          |
| football_odds_prematch        | match_date      | fixture_id, bookmaker          |
| football_standings            | season          | league_id, team_id             |
| football_teams                | —               | team_id, country               |
| football_players              | season          | player_id, team_id             |
| football_injuries             | match_date      | team_id, player_id             |
| football_leagues              | —               | league_id                      |

**Gold:**

| Tabela                   | PARTITION BY    | ZORDER BY                        |
|--------------------------|-----------------|----------------------------------|
| fct_match_features       | season          | fixture_id, league_id            |
| fct_team_form            | season          | team_id, league_id               |
| fct_team_strength        | —               | team_id                          |
| fct_head_to_head         | —               | home_team_id, away_team_id       |
| fct_player_impact        | season          | player_id, team_id               |
| fct_odds_consensus       | match_date      | fixture_id                       |
| fct_match_predictions    | match_date      | fixture_id, model_version        |
| fct_model_performance    | —               | model_version                    |

---

## 6. Agents e Skills — Domínio Football

### 6.1 Mapa de Agents

O domínio Football introduz **6 Agents especializados** que se encaixam na DAG orquestrada pelo Airflow.

```
┌─────────────────────────────────────────────────────────────┐
│              football_daily_pipeline (DAG)                    │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  1. FootballIngestionAgent                              │  │
│  │     Coleta dados da API-Football → Bronze               │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │  2. FootballProcessingAgent                             │  │
│  │     Bronze → Silver (flatten, dedup, tipagem)           │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │  3. FootballDBTAgent                                    │  │
│  │     Silver → Gold (features, marts, ratings)            │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │  4. FootballMLAgent                                     │  │
│  │     Treino + geração de predições                       │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │  5. FootballServingAgent                                │  │
│  │     Gold + Predições → PostgreSQL                       │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │  6. FootballQualityAgent                                │  │
│  │     Validação de qualidade pós-pipeline                 │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Skills por Agent

**FootballIngestionAgent**

| Skill                              | Endpoint API-Football                     | Responsabilidade                       |
|------------------------------------|-------------------------------------------|----------------------------------------|
| api_football_leagues_extractor     | /leagues                                  | Ligas e cobertura disponível           |
| api_football_fixtures_extractor    | /fixtures                                 | Partidas por liga/data (incremental)   |
| api_football_statistics_extractor  | /fixtures/statistics                      | Stats por time/partida                 |
| api_football_events_extractor      | /fixtures/events                          | Gols, cartões, substituições           |
| api_football_lineups_extractor     | /fixtures/lineups                         | Escalações                             |
| api_football_players_extractor     | /fixtures/players                         | Stats individuais por partida          |
| api_football_odds_extractor        | /odds                                     | Odds pré-jogo                          |
| api_football_standings_extractor   | /standings                                | Classificação atualizada               |
| api_football_injuries_extractor    | /injuries                                 | Lesões e suspensões                    |
| api_football_predictions_extractor | /predictions                              | Predições da própria API               |
| api_football_teams_extractor       | /teams                                    | Dados cadastrais de times              |
| api_football_quota_monitor         | Header x-ratelimit-remaining              | Monitoramento de quota consumida       |

**FootballProcessingAgent**

| Skill                              | Responsabilidade                                        |
|-------------------------------------|---------------------------------------------------------|
| spark_football_fixtures_flatten     | Flatten JSON de fixtures, extrair campos tipados         |
| spark_football_statistics_flatten   | Normalizar statistics (pivot de tipos de stat)           |
| spark_football_events_normalize     | Normalizar eventos com classificação por tipo            |
| spark_football_odds_normalize       | Consolidar odds por bookmaker, calcular consenso         |
| spark_football_dedup                | Deduplicação global por fixture_id                       |
| spark_football_key_generator        | Criar surrogate keys compostas                           |

**FootballDBTAgent**

| Skill              | Responsabilidade                                     |
|---------------------|------------------------------------------------------|
| dbt_football_run    | Executar modelos staging → intermediate → mart       |
| dbt_football_test   | Rodar unit tests + schema tests + singular tests     |
| dbt_football_docs   | Gerar documentação com lineage                       |

**FootballMLAgent**

| Skill                              | Responsabilidade                                      |
|-------------------------------------|-------------------------------------------------------|
| ml_feature_store_loader             | Carregar fct_match_features para treino                |
| ml_model_training                   | Treinar ensemble (RandomForest + XGBoost + LightGBM)  |
| ml_model_evaluation                 | Avaliar com log_loss, accuracy, brier_score            |
| ml_model_registry                   | Registrar modelo no MLflow com métricas                |
| ml_prediction_generator             | Gerar probabilidades para partidas futuras             |
| ml_prediction_writer                | Escrever predições na Gold (fct_match_predictions)     |

**FootballServingAgent**

| Skill                              | Responsabilidade                                      |
|-------------------------------------|-------------------------------------------------------|
| postgres_predictions_upsert         | UPSERT predições no serving.match_predictions         |
| postgres_standings_upsert           | UPSERT classificação no serving.league_standings      |
| postgres_team_form_upsert           | UPSERT forma recente no serving.team_form             |
| postgres_fixtures_upsert            | UPSERT próximas partidas no serving.upcoming_fixtures |
| cache_invalidator                   | Invalidar cache da API após atualização               |

**FootballQualityAgent**

| Skill                              | Responsabilidade                                      |
|-------------------------------------|-------------------------------------------------------|
| quality_fixture_count_check         | Validar que não há partidas faltando por rodada        |
| quality_odds_range_check            | Validar que odds estão entre 1.01 e 100.00            |
| quality_prediction_sum_check        | Validar que prob_home + prob_draw + prob_away ≈ 1.0   |
| quality_freshness_check             | Validar que dados não estão defasados                  |
| quality_model_drift_check           | Detectar degradação de acurácia do modelo              |

---

## 7. Features para o Modelo de ML

### 7.1 Tabela `fct_match_features` — Feature Matrix

Esta é a tabela central que alimenta o modelo de predição. Cada linha representa uma partida com todas as features calculadas no momento anterior ao jogo.

**Regra fundamental**: features são calculadas usando **apenas dados disponíveis antes do jogo**. Usar dados do próprio jogo (goals_home, statistics) para prever o resultado desse jogo é data leakage.

**Grupos de Features:**

| Grupo                  | Features                                                     | Fonte Silver/Gold         |
|------------------------|--------------------------------------------------------------|---------------------------|
| Identificação          | fixture_id, match_date, league_id, season, round             | football_fixtures         |
| Times                  | home_team_id, away_team_id                                   | football_fixtures         |
| Forma Recente (Home)   | home_wins_last_5, home_draws_last_5, home_losses_last_5, home_goals_scored_avg_5, home_goals_conceded_avg_5, home_points_last_5 | fct_team_form |
| Forma Recente (Away)   | away_wins_last_5, away_draws_last_5, away_losses_last_5, away_goals_scored_avg_5, away_goals_conceded_avg_5, away_points_last_5 | fct_team_form |
| Forma Casa/Fora        | home_home_wins_last_5, away_away_wins_last_5 (performance como mandante/visitante especificamente) | fct_team_form |
| ELO Rating             | home_elo_rating, away_elo_rating, elo_diff                   | fct_team_strength         |
| Head to Head           | h2h_home_wins, h2h_draws, h2h_away_wins, h2h_total_games, h2h_home_goals_avg, h2h_away_goals_avg | fct_head_to_head |
| Odds de Mercado        | odd_home_avg, odd_draw_avg, odd_away_avg, odd_home_max, odd_away_max, odd_over25_avg, odd_btts_avg | fct_odds_consensus |
| Classificação          | home_position, away_position, home_points, away_points, position_diff | football_standings |
| Desfalques             | home_injuries_count, away_injuries_count, home_key_players_out, away_key_players_out | football_injuries + fct_player_impact |
| Predição API           | api_pred_home_pct, api_pred_draw_pct, api_pred_away_pct      | football_api_predictions  |
| Contexto               | is_derby, is_cup_match, days_since_last_match_home, days_since_last_match_away | Derivado |
| Target                 | result (H / D / A) — **apenas para partidas já realizadas**  | football_fixtures         |

### 7.2 Cálculo de ELO Rating

O sistema ELO é um rating numérico que reflete a força relativa de cada time. Princípios:

- Rating inicial: 1500 para todos os times.
- Fator K: 20 para ligas nacionais, 30 para copas internacionais, 40 para finais.
- Ajuste por margem de gols: multiplicador logarítmico `ln(goal_diff + 1)`.
- Home advantage: bônus de 100 pontos ao rating do mandante no cálculo do expected score.
- Atualização: após cada partida, baseado no resultado real vs esperado.
- Decaimento: regressão de 10% ao valor médio (1500) no início de cada temporada.

O ELO é calculado no dbt como modelo incremental, processando partidas em ordem cronológica.

### 7.3 Modelo de ML — Arquitetura

| Aspecto            | Definição                                                   |
|--------------------|-------------------------------------------------------------|
| Tipo               | Classificação multiclasse (H / D / A)                      |
| Abordagem          | Stacking Ensemble                                           |
| Modelos Base       | RandomForest, XGBoost, LightGBM                            |
| Meta-learner       | Logistic Regression (calibrado)                              |
| Output             | prob_home_win, prob_draw, prob_away_win (somam ≈ 1.0)       |
| Métricas           | Log Loss (primária), Accuracy, Brier Score, ROC AUC         |
| Validação          | Time-series split (nunca usar dados futuros para treinar)   |
| Retreino           | Semanal (após rodada completa)                              |
| Registry           | MLflow (modelo versionado, métricas rastreadas)             |
| Threshold          | Modelo só entra em produção se log_loss < modelo anterior   |

**Regras para o agente:**

- Nunca usar random split para validação. Futebol é temporal — usar time-series cross-validation.
- O modelo treina com dados de temporadas anteriores e da temporada atual até a última rodada completa.
- Predições são geradas apenas para partidas com status "Not Started" na API-Football.
- O stacking ensemble deve ser treinado em 2 fases: modelos base via cross-validation, meta-learner nos out-of-fold predictions.
- Odds do mercado são features, não targets. O modelo prevê resultado, não odds.

---

## 8. dbt — Estrutura de Modelos Football

### 8.1 Organização

```
dbt_project/models/
│
├── staging/
│   ├── football/
│   │   ├── _football_sources.yml          ← sources Silver
│   │   ├── stg_football_fixtures.sql
│   │   ├── stg_football_match_statistics.sql
│   │   ├── stg_football_match_events.sql
│   │   ├── stg_football_odds_prematch.sql
│   │   ├── stg_football_standings.sql
│   │   ├── stg_football_injuries.sql
│   │   ├── stg_football_players.sql
│   │   └── stg_football_api_predictions.sql
│   │
├── intermediate/
│   ├── football/
│   │   ├── int_football_team_form.sql          ← últimos 5/10 jogos
│   │   ├── int_football_elo_ratings.sql        ← cálculo ELO incremental
│   │   ├── int_football_head_to_head.sql       ← confrontos diretos
│   │   ├── int_football_odds_consensus.sql     ← média/mediana de odds
│   │   ├── int_football_player_impact.sql      ← impacto estatístico
│   │   └── int_football_match_context.sql      ← derbies, descanso, etc
│   │
└── mart/
    ├── football/
    │   ├── _football_mart_schema.yml           ← schema tests
    │   ├── _football_mart_docs.md              ← documentação
    │   ├── fct_match_features.sql              ← feature matrix
    │   ├── fct_team_form.sql
    │   ├── fct_team_strength.sql
    │   ├── fct_head_to_head.sql
    │   ├── fct_player_impact.sql
    │   ├── fct_odds_consensus.sql
    │   ├── fct_match_predictions.sql
    │   ├── fct_model_performance.sql
    │   ├── fct_league_summary.sql
    │   ├── fct_team_season_stats.sql
    │   ├── dim_teams.sql
    │   ├── dim_leagues.sql
    │   └── dim_players.sql
```

### 8.2 Lineage — Grafo de Dependências

```
Sources (Silver)                Staging              Intermediate              Mart (Gold)
─────────────────              ─────────            ──────────────            ────────────

football_fixtures         → stg_fixtures       ──→ int_team_form        ──→ fct_team_form
                                               ──→ int_elo_ratings      ──→ fct_team_strength
                                               ──→ int_head_to_head     ──→ fct_head_to_head
                                               ──→ int_match_context    ──┐
                                                                          │
football_match_statistics → stg_match_stats    ──────────────────────────┤
                                                                          │
football_match_events     → stg_match_events   ──────────────────────────┤
                                                                          │
football_odds_prematch    → stg_odds           ──→ int_odds_consensus   ──┤
                                                                          │
football_standings        → stg_standings      ──────────────────────────┤
                                                                          │
football_injuries         → stg_injuries       ──────────────────────────┤
                                                                          │
football_players          → stg_players        ──→ int_player_impact    ──┤
                                                                          │
football_api_predictions  → stg_api_preds      ──────────────────────────┤
                                                                          ▼
                                                                   fct_match_features
                                                                          │
                                                                   (input para ML)
                                                                          │
                                                                          ▼
                                                                   fct_match_predictions
                                                                   fct_model_performance
```

### 8.3 Testes dbt — Estratégia para Football

**Unit Tests:**

| Modelo            | Teste                                       | O que valida                              |
|-------------------|---------------------------------------------|-------------------------------------------|
| fct_team_form     | test_form_calculation                       | Wins+Draws+Losses = total de jogos        |
| fct_team_form     | test_form_window                            | Usa exatamente últimos 5 jogos            |
| fct_match_features| test_no_data_leakage                        | Features calculadas antes da data do jogo |
| fct_match_features| test_result_values                          | Target é H, D ou A exclusivamente         |
| fct_team_strength | test_elo_initial_rating                     | Time novo começa com 1500                 |
| fct_team_strength | test_elo_zero_sum                           | Pontos ganhos = pontos perdidos           |
| fct_odds_consensus| test_odds_above_one                         | Todas as odds > 1.0                       |

**Schema Tests:**

| Modelo              | Coluna           | Teste                                |
|----------------------|------------------|--------------------------------------|
| fct_match_features   | fixture_id       | unique, not_null                     |
| fct_match_features   | result           | accepted_values: [H, D, A]          |
| fct_match_features   | odd_home_avg     | dbt_expectations: between(1.01, 50)  |
| fct_team_form        | team_id          | not_null                             |
| fct_team_form        | wins_last_5      | dbt_expectations: between(0, 5)      |
| fct_match_predictions| fixture_id       | unique, not_null                     |
| fct_match_predictions| prob_home_win    | dbt_expectations: between(0, 1)      |
| fct_model_performance| log_loss         | dbt_expectations: between(0, 5)      |

**Singular Tests:**

| Teste                                 | O que valida                                          |
|---------------------------------------|-------------------------------------------------------|
| assert_no_future_features             | Nenhuma feature usa dados posteriores à data do jogo  |
| assert_prediction_probabilities_sum   | prob_home + prob_draw + prob_away entre 0.95 e 1.05   |
| assert_elo_rating_reasonable          | Todos os ELOs entre 800 e 2200                        |
| assert_no_orphan_statistics           | Toda statistic tem fixture correspondente              |
| assert_complete_rounds                | Rodada completa tem N jogos esperados para a liga      |

---

## 9. PostgreSQL Serving — Tabelas Football

### 9.1 Schema

O domínio Football usa o schema `serving` do PostgreSQL Serving (porta 5433), com tabelas prefixadas por domínio.

| Tabela                          | Propósito                              | Atualização     |
|---------------------------------|----------------------------------------|-----------------|
| serving.match_predictions       | Predições para partidas futuras        | Diária          |
| serving.upcoming_fixtures       | Próximas partidas com dados básicos    | Diária          |
| serving.league_standings        | Classificação atualizada               | Diária          |
| serving.team_form               | Forma recente dos times                | Diária          |
| serving.model_metrics           | Performance dos modelos                | Semanal         |
| serving.historical_predictions  | Predições passadas com resultado real  | Diária (append) |

### 9.2 Regras para o agente

- Toda tabela de serving tem constraint de PRIMARY KEY e índice no campo de consulta principal.
- `match_predictions` usa UPSERT por `fixture_id` — nunca deletar predições anteriores.
- `historical_predictions` é append-only — preserva todas as predições geradas com `model_version` e `created_at`.
- Toda carga registra na tabela `audit.pipeline_execution`.
- Materialized Views para queries de dashboard (top N times, previsões da rodada).

---

## 10. API REST — Camada de Consumo

### 10.1 Princípio

A API REST opera **fora do Airflow**, como serviço independente. Ela consome dados do PostgreSQL Serving e não tem acesso direto ao Databricks ou ao pipeline. Isso respeita o princípio de separação do PRD pai.

### 10.2 Endpoints

| Método | Rota                                    | Propósito                                  | Fonte PostgreSQL           |
|--------|-----------------------------------------|--------------------------------------------|----------------------------|
| GET    | /api/v1/predictions/{fixture_id}        | Predição para uma partida específica       | serving.match_predictions  |
| GET    | /api/v1/predictions/league/{league_id}  | Predições da próxima rodada de uma liga    | serving.match_predictions  |
| GET    | /api/v1/predictions/today               | Predições dos jogos de hoje                | serving.match_predictions  |
| GET    | /api/v1/fixtures/upcoming               | Próximas partidas com dados e predições    | serving.upcoming_fixtures  |
| GET    | /api/v1/standings/{league_id}           | Classificação atualizada                   | serving.league_standings   |
| GET    | /api/v1/teams/{team_id}/form            | Forma recente do time                      | serving.team_form          |
| GET    | /api/v1/model/metrics                   | Métricas de performance do modelo          | serving.model_metrics      |
| GET    | /api/v1/model/history                   | Histórico de predições vs resultados reais | serving.historical_predictions |
| GET    | /health                                 | Health check da API                         | —                          |

### 10.3 Response Model — Predição

```
{
  "fixture_id": 1208021,
  "league": "Brasileirão Série A",
  "match_date": "2026-04-05",
  "home_team": "Flamengo",
  "away_team": "Palmeiras",
  "prediction": {
    "home_win": 0.42,
    "draw": 0.28,
    "away_win": 0.30,
    "confidence": "medium",
    "model_version": "v1.3.2",
    "generated_at": "2026-04-04T18:30:00Z"
  },
  "context": {
    "home_form": "WDWWL",
    "away_form": "WWDWW",
    "home_elo": 1687,
    "away_elo": 1712,
    "h2h_last_5": "2W 1D 2L",
    "market_odds": {
      "home": 2.35,
      "draw": 3.40,
      "away": 2.90
    }
  }
}
```

---

## 11. DAG — Orquestração

### 11.1 DAGs do Domínio Football

| DAG                            | Schedule       | Propósito                                   |
|--------------------------------|----------------|---------------------------------------------|
| football_daily_pipeline        | 0 6 * * *      | Pipeline completo: ingestão → predição      |
| football_matchday_pipeline     | 0 10 * * 3,6,7 | Coleta extra em dias de jogo (qua, sáb, dom)|
| football_weekly_retrain        | 0 4 * * 1      | Retreino do modelo ML (toda segunda)        |
| football_weekly_maintenance    | 0 2 * * 0      | OPTIMIZE + VACUUM + ANALYZE (todo domingo)  |
| football_season_init           | Manual         | Backfill de temporada nova                   |

### 11.2 Dependências — football_daily_pipeline

```
start
  │
  ├──→ football_ingestion_agent
  │       │
  │       ├──→ api_football_fixtures_extractor
  │       ├──→ api_football_statistics_extractor
  │       ├──→ api_football_events_extractor
  │       ├──→ api_football_odds_extractor
  │       ├──→ api_football_standings_extractor
  │       └──→ api_football_quota_monitor
  │
  ├──→ football_processing_agent
  │       │
  │       ├──→ spark_football_fixtures_flatten
  │       ├──→ spark_football_statistics_flatten
  │       ├──→ spark_football_odds_normalize
  │       └──→ spark_football_dedup
  │
  ├──→ football_dbt_agent
  │       │
  │       ├──→ dbt_football_run
  │       └──→ dbt_football_test
  │
  ├──→ football_ml_agent (se modelo existente)
  │       │
  │       ├──→ ml_feature_store_loader
  │       └──→ ml_prediction_generator
  │
  ├──→ football_serving_agent
  │       │
  │       ├──→ postgres_predictions_upsert
  │       ├──→ postgres_standings_upsert
  │       └──→ postgres_fixtures_upsert
  │
  ├──→ football_quality_agent
  │       │
  │       ├──→ quality_fixture_count_check
  │       ├──→ quality_prediction_sum_check
  │       └──→ quality_freshness_check
  │
  └──→ end
```

---

## 12. Diferencial Competitivo

O que torna este sistema diferente de um dashboard comum da API-Football:

| Aspecto               | Dashboard comum         | Football Prediction Engine            |
|-----------------------|-------------------------|---------------------------------------|
| Dados                 | Consome e exibe          | Coleta, modela, transforma e prevê    |
| Predição              | Usa da API (6 algoritmos)| Modelo próprio treinado continuamente |
| Rastreabilidade       | Nenhuma                  | Cada predição versionada com métricas |
| Escalabilidade        | Limitada ao frontend     | Databricks + Medallion + ML pipeline  |
| Retreino              | Não aplicável            | Semanal com validação automática      |
| Monetização potencial | Consumo informacional    | API de predições como produto         |
| Qualidade de dados    | Confiança na fonte       | Testes em 3 níveis + quality agent    |

---

## 13. Roadmap — Football Prediction Engine

| Fase   | Escopo                                                         | Prioridade |
|--------|----------------------------------------------------------------|------------|
| v1.0   | Ingestão + Medallion + dbt + Predição básica (Brasileirão)    | Atual      |
| v1.1   | ELO Rating + Head to Head + melhoria de features              | Alta       |
| v1.2   | MLflow + retreino automático + model performance tracking     | Alta       |
| v1.3   | FastAPI de predições + documentação API                       | Média      |
| v2.0   | Expansão para ligas europeias (P2)                            | Média      |
| v2.1   | Live odds integration + in-play features                      | Baixa      |
| v2.2   | Dashboard interativo (Superset ou React)                      | Baixa      |
| v3.0   | Under/Over, BTTS, e outros mercados de predição              | Futura     |
| v3.1   | Player-level predictions (artilheiro, assistências)           | Futura     |

---

## 14. Referências

| Recurso                    | URL                                              |
|----------------------------|--------------------------------------------------|
| API-Football Dashboard     | https://dashboard.api-football.com/              |
| API-Football Documentation | https://www.api-football.com/documentation-v3     |
| API-Football Endpoints     | https://www.api-football.com/news/category/endpoints |
| API-Football Tutorials     | https://www.api-football.com/tutorials/           |
| API-Sports (host alternativo) | https://api-sports.io/documentation/football/v3 |
| PRD MCP Platform (pai)     | PRD_ORIENTACAO_AGENTE_IA.md                      |
| Infra Setup                | INFRA_MCP_AGENT_DAG_PLATFORM.md                  |

---

> **Este documento é a referência arquitetural do Football Prediction Engine.**
> É extensão do PRD pai e herda todos os seus princípios.
> O agente de IA deve consultar ambos os documentos antes de qualquer decisão técnica no domínio Football.
> A implementação começa pelo Brasileirão Série A (league_id: 71) — sempre.
