-- ============================================================
-- 04_gold_ddl.sql
-- Tabelas Gold — marts prontos para consumo e features de ML.
--
-- Propriedades obrigatórias:
--   - delta.autoOptimize.optimizeWrite = true
--   - delta.autoOptimize.autoCompact   = true
--   - delta.logRetentionDuration       = 'interval 90 days'
--   - quality = 'gold'
--
-- Operação de escrita: overwrite idempotente ou MERGE
-- Geradas pelo dbt (fct_* e dim_*) ou pelas Skills de ML
-- ============================================================

USE CATALOG football_prediction;
USE SCHEMA gold;

-- ── Features de ML por partida (tabela central do modelo) ─────────────────────
CREATE TABLE IF NOT EXISTS fct_match_features (
  fixture_id                INT       NOT NULL COMMENT 'PK',
  league_id                 INT       NOT NULL,
  season                    INT       NOT NULL,
  match_date                DATE,

  -- Forma dos últimos 5 jogos
  home_wins_last_5          INT,
  home_draws_last_5         INT,
  home_losses_last_5        INT,
  home_goals_scored_avg_5   DOUBLE,
  home_goals_conceded_avg_5 DOUBLE,
  away_wins_last_5          INT,
  away_draws_last_5         INT,
  away_losses_last_5        INT,
  away_goals_scored_avg_5   DOUBLE,
  away_goals_conceded_avg_5 DOUBLE,

  -- ELO
  home_elo_rating           INT,
  away_elo_rating           INT,
  elo_diff                  INT       COMMENT 'home_elo - away_elo',

  -- Head-to-head
  h2h_home_wins             INT,
  h2h_draws                 INT,
  h2h_away_wins             INT,

  -- Odds consenso (média de bookmakers)
  odd_home_avg              DOUBLE,
  odd_draw_avg              DOUBLE,
  odd_away_avg              DOUBLE,

  -- Posição na tabela
  home_position             INT,
  away_position             INT,
  position_diff             INT       COMMENT 'home_position - away_position',

  -- Lesões
  home_injuries_count       INT,
  away_injuries_count       INT,

  -- Predições da API (features externas)
  api_pred_home_pct         DOUBLE,
  api_pred_draw_pct         DOUBLE,
  api_pred_away_pct         DOUBLE,

  -- Contexto da partida
  is_derby                  BOOLEAN,
  days_since_last_match_home INT,
  days_since_last_match_away INT,

  -- Target (NULL para partidas futuras)
  result                    STRING    COMMENT 'H / D / A — NULL para partidas ainda não realizadas',

  _loaded_at                TIMESTAMP NOT NULL,
  _batch_id                 STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (match_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 90 days',
  'quality'                          = 'gold'
)
COMMENT 'ML feature store — one row per fixture. Consumed by MLFeatureStoreLoader skill.';

-- OPTIMIZE football_prediction.gold.fct_match_features ZORDER BY (fixture_id, league_id, match_date);

-- ── Predições do modelo ML ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fct_match_predictions (
  fixture_id         INT       NOT NULL COMMENT 'PK',
  league_id          INT,
  season             INT,
  match_date         DATE,
  home_team_id       INT,
  home_team_name     STRING,
  away_team_id       INT,
  away_team_name     STRING,
  prob_home_win      DOUBLE    COMMENT 'Probabilidade vitória mandante (0-1)',
  prob_draw          DOUBLE    COMMENT 'Probabilidade empate (0-1)',
  prob_away_win      DOUBLE    COMMENT 'Probabilidade vitória visitante (0-1)',
  predicted_result   STRING    COMMENT 'H / D / A — resultado de maior probabilidade',
  confidence         STRING    COMMENT 'high (>55%) / medium (>40%) / low (<=40%)',
  model_version      STRING    NOT NULL,
  generated_at       TIMESTAMP NOT NULL,
  _loaded_at         TIMESTAMP NOT NULL,
  _batch_id          STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (match_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 90 days',
  'quality'                          = 'gold'
)
COMMENT 'ML model predictions — MERGE by fixture_id. Latest prediction per fixture.';

-- OPTIMIZE football_prediction.gold.fct_match_predictions ZORDER BY (fixture_id, model_version);

-- ── Forma dos times ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fct_team_form (
  team_id              INT       NOT NULL,
  league_id            INT       NOT NULL,
  season               INT       NOT NULL,
  reference_date       DATE      NOT NULL COMMENT 'Data de referência do cálculo',
  wins_last_5          INT,
  draws_last_5         INT,
  losses_last_5        INT,
  goals_scored_avg_5   DOUBLE,
  goals_conceded_avg_5 DOUBLE,
  points_last_5        INT,
  form_string          STRING    COMMENT 'Sequência ex: WWDLW',
  elo_rating           INT,
  _loaded_at           TIMESTAMP NOT NULL,
  _batch_id            STRING    NOT NULL
)
USING DELTA
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 90 days',
  'quality'                          = 'gold'
)
COMMENT 'Rolling team form — MERGE by (team_id, league_id, season, reference_date).';

-- ── Head-to-head histórico ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fct_head_to_head (
  home_team_id    INT     NOT NULL,
  away_team_id    INT     NOT NULL,
  league_id       INT     NOT NULL,
  total_matches   INT,
  home_wins       INT,
  draws           INT,
  away_wins       INT,
  home_goals_avg  DOUBLE,
  away_goals_avg  DOUBLE,
  _loaded_at      TIMESTAMP NOT NULL,
  _batch_id       STRING    NOT NULL
)
USING DELTA
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 90 days',
  'quality'                          = 'gold'
)
COMMENT 'Head-to-head statistics — MERGE by (home_team_id, away_team_id, league_id).';

-- ── Resumo da liga ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fct_league_summary (
  league_id     INT     NOT NULL,
  league_name   STRING,
  season        INT     NOT NULL,
  total_matches INT,
  matches_played INT,
  matches_pending INT,
  home_win_pct  DOUBLE,
  draw_pct      DOUBLE,
  away_win_pct  DOUBLE,
  avg_goals     DOUBLE,
  _loaded_at    TIMESTAMP NOT NULL,
  _batch_id     STRING    NOT NULL
)
USING DELTA
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 90 days',
  'quality'                          = 'gold'
)
COMMENT 'League-level summary statistics — MERGE by (league_id, season).';

-- ── Dimensão times ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_teams (
  team_id      INT     NOT NULL COMMENT 'PK',
  team_name    STRING  NOT NULL,
  team_code    STRING,
  country      STRING,
  founded      INT,
  logo_url     STRING,
  venue_name   STRING,
  venue_city   STRING,
  venue_capacity INT,
  _loaded_at   TIMESTAMP NOT NULL
)
USING DELTA
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 90 days',
  'quality'                          = 'gold'
)
COMMENT 'Team dimension — MERGE by team_id. Weekly refresh.';

-- ── Dimensão ligas ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_leagues (
  league_id    INT     NOT NULL COMMENT 'PK',
  league_name  STRING  NOT NULL,
  league_type  STRING  COMMENT 'League / Cup',
  country      STRING,
  logo_url     STRING,
  flag_url     STRING,
  season       INT,
  _loaded_at   TIMESTAMP NOT NULL
)
USING DELTA
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 90 days',
  'quality'                          = 'gold'
)
COMMENT 'League dimension — MERGE by (league_id, season). Weekly refresh.';

-- Verificação
SHOW TABLES IN football_prediction.gold;
