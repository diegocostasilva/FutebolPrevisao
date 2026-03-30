-- ============================================================
-- 03_silver_ddl.sql
-- Tabelas Silver — dados limpos, tipados e deduplicados.
--
-- Propriedades obrigatórias:
--   - delta.autoOptimize.optimizeWrite = true
--   - delta.autoOptimize.autoCompact   = true
--   - delta.logRetentionDuration       = 'interval 60 days'
--   - quality = 'silver'
--
-- Operação de escrita: MERGE upsert (nunca INSERT puro)
-- Particionamento: match_date (DATE)
-- ZORDER: colunas de filtro frequente (max 4)
-- ============================================================

USE CATALOG football_prediction;
USE SCHEMA silver;

-- ── Partidas (tabela central) ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_fixtures (
  fixture_id       INT       NOT NULL COMMENT 'PK — ID da partida na API-Football',
  league_id        INT       NOT NULL,
  league_name      STRING,
  season           INT       NOT NULL,
  match_date       DATE,
  match_ts         TIMESTAMP COMMENT 'Data/hora exata com fuso horário',
  home_team_id     INT       NOT NULL,
  home_team_name   STRING,
  away_team_id     INT       NOT NULL,
  away_team_name   STRING,
  goals_home       INT,
  goals_away       INT,
  result           STRING    COMMENT 'H / D / A — preenchido apenas para status FT',
  status           STRING    COMMENT 'NS, 1H, HT, 2H, FT, AET, PEN, CANC, PST, ...',
  round            STRING,
  venue            STRING,
  referee          STRING,
  _loaded_at       TIMESTAMP NOT NULL,
  _batch_id        STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (match_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 60 days',
  'quality'                          = 'silver'
)
COMMENT 'Cleaned fixtures — one row per match. MERGE upsert by fixture_id.';

-- OPTIMIZE após carga inicial:
-- OPTIMIZE football_prediction.silver.football_fixtures ZORDER BY (fixture_id, league_id);

-- ── Estatísticas de partida ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_match_statistics (
  fixture_id              INT       NOT NULL,
  team_id                 INT       NOT NULL,
  match_date              DATE,
  shots_on_goal           INT,
  shots_off_goal          INT,
  total_shots             INT,
  blocked_shots           INT,
  shots_inside_box        INT,
  shots_outside_box       INT,
  fouls                   INT,
  corner_kicks            INT,
  offsides                INT,
  ball_possession         DOUBLE    COMMENT 'Porcentagem 0-100',
  yellow_cards            INT,
  red_cards               INT,
  goalkeeper_saves        INT,
  total_passes            INT,
  passes_accurate         INT,
  passes_pct              DOUBLE,
  expected_goals          DOUBLE,
  _loaded_at              TIMESTAMP NOT NULL,
  _batch_id               STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (match_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 60 days',
  'quality'                          = 'silver'
)
COMMENT 'Pivoted match statistics — one row per (fixture_id, team_id). MERGE by PK.';

-- OPTIMIZE football_prediction.silver.football_match_statistics ZORDER BY (fixture_id, team_id);

-- ── Eventos de partida ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_match_events (
  fixture_id      INT       NOT NULL,
  team_id         INT       NOT NULL,
  player_id       INT,
  player_name     STRING,
  event_type      STRING    COMMENT 'Goal / Card / Subst / Var',
  event_detail    STRING    COMMENT 'Normal Goal / Yellow Card / Red Card / Penalty / Own Goal / ...',
  time_elapsed    INT       COMMENT 'Minuto do evento',
  time_extra      INT       COMMENT 'Tempo acrescido',
  match_date      DATE,
  _loaded_at      TIMESTAMP NOT NULL,
  _batch_id       STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (match_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 60 days',
  'quality'                          = 'silver'
)
COMMENT 'Normalized match events — goals, cards, substitutions.';

-- OPTIMIZE football_prediction.silver.football_match_events ZORDER BY (fixture_id, team_id);

-- ── Odds pré-jogo ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_odds_prematch (
  fixture_id       INT       NOT NULL,
  bookmaker_id     INT,
  bookmaker_name   STRING    NOT NULL,
  odd_home         DOUBLE,
  odd_draw         DOUBLE,
  odd_away         DOUBLE,
  match_date       DATE,
  _loaded_at       TIMESTAMP NOT NULL,
  _batch_id        STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (match_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 60 days',
  'quality'                          = 'silver'
)
COMMENT 'Pre-match odds — Match Winner market (1X2). MERGE by (fixture_id, bookmaker_name).';

-- OPTIMIZE football_prediction.silver.football_odds_prematch ZORDER BY (fixture_id, bookmaker_name);

-- ── Classificação ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_standings (
  league_id        INT       NOT NULL,
  team_id          INT       NOT NULL,
  season           INT       NOT NULL,
  position         INT,
  team_name        STRING,
  played           INT,
  wins             INT,
  draws            INT,
  losses           INT,
  goals_for        INT,
  goals_against    INT,
  goal_diff        INT,
  points           INT,
  form             STRING    COMMENT 'Últimos 5 resultados ex: WWDLW',
  _loaded_at       TIMESTAMP NOT NULL,
  _batch_id        STRING    NOT NULL
)
USING DELTA
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 60 days',
  'quality'                          = 'silver'
)
COMMENT 'League standings — MERGE by (league_id, team_id, season).';

-- OPTIMIZE football_prediction.silver.football_standings ZORDER BY (league_id, season);

-- ── Lesões ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_injuries (
  fixture_id       INT,
  league_id        INT       NOT NULL,
  season           INT       NOT NULL,
  team_id          INT       NOT NULL,
  player_id        INT       NOT NULL,
  player_name      STRING,
  injury_type      STRING,
  injury_reason    STRING,
  match_date       DATE,
  _loaded_at       TIMESTAMP NOT NULL,
  _batch_id        STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (match_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 60 days',
  'quality'                          = 'silver'
)
COMMENT 'Injuries per player/fixture — MERGE by (player_id, fixture_id).';

-- Verificação
SHOW TABLES IN football_prediction.silver;
