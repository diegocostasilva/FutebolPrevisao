-- ============================================================
-- 02_bronze_ddl.sql
-- Tabelas Bronze — JSON bruto da API-Football.
--
-- Padrão de todas as tabelas Bronze:
--   - payload   STRING  → JSON completo do response da API
--   - endpoint  STRING  → endpoint chamado (ex: "fixtures")
--   - _ingestion_date  DATE       → partição principal
--   - _ingestion_ts    TIMESTAMP  → timestamp UTC da ingestão
--   - _batch_id        STRING     → UUID do batch (para reprocessamento)
--   - _source_endpoint STRING     → endpoint fonte
--
-- Propriedades obrigatórias:
--   - delta.autoOptimize.optimizeWrite = true
--   - delta.autoOptimize.autoCompact   = true
--   - delta.logRetentionDuration       = 'interval 30 days'
--   - quality = 'bronze'
-- ============================================================

USE CATALOG mcp_platform;
USE SCHEMA bronze;

-- ── Partidas ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_fixtures_raw (
  payload            STRING    NOT NULL COMMENT 'JSON bruto do response /fixtures',
  endpoint           STRING    NOT NULL,
  _ingestion_date    DATE      NOT NULL,
  _ingestion_ts      TIMESTAMP NOT NULL,
  _batch_id          STRING    NOT NULL,
  _source_endpoint   STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (_ingestion_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 30 days',
  'quality'                          = 'bronze'
)
COMMENT 'Raw fixtures from /fixtures endpoint — append-only';

-- ── Estatísticas de partida ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_statistics_raw (
  payload            STRING    NOT NULL COMMENT 'JSON bruto do response /fixtures/statistics',
  endpoint           STRING    NOT NULL,
  _ingestion_date    DATE      NOT NULL,
  _ingestion_ts      TIMESTAMP NOT NULL,
  _batch_id          STRING    NOT NULL,
  _source_endpoint   STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (_ingestion_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 30 days',
  'quality'                          = 'bronze'
)
COMMENT 'Raw match statistics from /fixtures/statistics — append-only';

-- ── Eventos (gols, cartões, substituições) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_events_raw (
  payload            STRING    NOT NULL COMMENT 'JSON bruto do response /fixtures/events',
  endpoint           STRING    NOT NULL,
  _ingestion_date    DATE      NOT NULL,
  _ingestion_ts      TIMESTAMP NOT NULL,
  _batch_id          STRING    NOT NULL,
  _source_endpoint   STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (_ingestion_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 30 days',
  'quality'                          = 'bronze'
)
COMMENT 'Raw match events from /fixtures/events — append-only';

-- ── Escalações ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_lineups_raw (
  payload            STRING    NOT NULL COMMENT 'JSON bruto do response /fixtures/lineups',
  endpoint           STRING    NOT NULL,
  _ingestion_date    DATE      NOT NULL,
  _ingestion_ts      TIMESTAMP NOT NULL,
  _batch_id          STRING    NOT NULL,
  _source_endpoint   STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (_ingestion_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 30 days',
  'quality'                          = 'bronze'
)
COMMENT 'Raw lineups from /fixtures/lineups — append-only';

-- ── Stats de jogadores por partida ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_players_stats_raw (
  payload            STRING    NOT NULL COMMENT 'JSON bruto do response /fixtures/players',
  endpoint           STRING    NOT NULL,
  _ingestion_date    DATE      NOT NULL,
  _ingestion_ts      TIMESTAMP NOT NULL,
  _batch_id          STRING    NOT NULL,
  _source_endpoint   STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (_ingestion_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 30 days',
  'quality'                          = 'bronze'
)
COMMENT 'Raw player statistics from /fixtures/players — append-only';

-- ── Odds pré-jogo ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_odds_raw (
  payload            STRING    NOT NULL COMMENT 'JSON bruto do response /odds',
  endpoint           STRING    NOT NULL,
  _ingestion_date    DATE      NOT NULL,
  _ingestion_ts      TIMESTAMP NOT NULL,
  _batch_id          STRING    NOT NULL,
  _source_endpoint   STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (_ingestion_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 30 days',
  'quality'                          = 'bronze'
)
COMMENT 'Raw pre-match odds from /odds — append-only';

-- ── Odds ao vivo ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_odds_live_raw (
  payload            STRING    NOT NULL COMMENT 'JSON bruto do response /odds/live',
  endpoint           STRING    NOT NULL,
  _ingestion_date    DATE      NOT NULL,
  _ingestion_ts      TIMESTAMP NOT NULL,
  _batch_id          STRING    NOT NULL,
  _source_endpoint   STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (_ingestion_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 30 days',
  'quality'                          = 'bronze'
)
COMMENT 'Raw live odds from /odds/live — append-only';

-- ── Predições da API (features para ML) ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_predictions_raw (
  payload            STRING    NOT NULL COMMENT 'JSON bruto do response /predictions',
  endpoint           STRING    NOT NULL,
  _ingestion_date    DATE      NOT NULL,
  _ingestion_ts      TIMESTAMP NOT NULL,
  _batch_id          STRING    NOT NULL,
  _source_endpoint   STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (_ingestion_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 30 days',
  'quality'                          = 'bronze'
)
COMMENT 'Raw API predictions from /predictions — used as ML features, not output';

-- ── Classificação ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_standings_raw (
  payload            STRING    NOT NULL COMMENT 'JSON bruto do response /standings',
  endpoint           STRING    NOT NULL,
  _ingestion_date    DATE      NOT NULL,
  _ingestion_ts      TIMESTAMP NOT NULL,
  _batch_id          STRING    NOT NULL,
  _source_endpoint   STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (_ingestion_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 30 days',
  'quality'                          = 'bronze'
)
COMMENT 'Raw standings from /standings — append-only';

-- ── Times ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_teams_raw (
  payload            STRING    NOT NULL COMMENT 'JSON bruto do response /teams',
  endpoint           STRING    NOT NULL,
  _ingestion_date    DATE      NOT NULL,
  _ingestion_ts      TIMESTAMP NOT NULL,
  _batch_id          STRING    NOT NULL,
  _source_endpoint   STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (_ingestion_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 30 days',
  'quality'                          = 'bronze'
)
COMMENT 'Raw team metadata from /teams — weekly refresh';

-- ── Jogadores ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_players_raw (
  payload            STRING    NOT NULL COMMENT 'JSON bruto do response /players',
  endpoint           STRING    NOT NULL,
  _ingestion_date    DATE      NOT NULL,
  _ingestion_ts      TIMESTAMP NOT NULL,
  _batch_id          STRING    NOT NULL,
  _source_endpoint   STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (_ingestion_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 30 days',
  'quality'                          = 'bronze'
)
COMMENT 'Raw player profiles from /players — append-only';

-- ── Lesões ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_injuries_raw (
  payload            STRING    NOT NULL COMMENT 'JSON bruto do response /injuries',
  endpoint           STRING    NOT NULL,
  _ingestion_date    DATE      NOT NULL,
  _ingestion_ts      TIMESTAMP NOT NULL,
  _batch_id          STRING    NOT NULL,
  _source_endpoint   STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (_ingestion_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 30 days',
  'quality'                          = 'bronze'
)
COMMENT 'Raw injuries from /injuries — append-only';

-- ── Técnicos ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_coaches_raw (
  payload            STRING    NOT NULL COMMENT 'JSON bruto do response /coachs',
  endpoint           STRING    NOT NULL,
  _ingestion_date    DATE      NOT NULL,
  _ingestion_ts      TIMESTAMP NOT NULL,
  _batch_id          STRING    NOT NULL,
  _source_endpoint   STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (_ingestion_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 30 days',
  'quality'                          = 'bronze'
)
COMMENT 'Raw coach data from /coachs — weekly refresh';

-- ── Transferências ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_transfers_raw (
  payload            STRING    NOT NULL COMMENT 'JSON bruto do response /transfers',
  endpoint           STRING    NOT NULL,
  _ingestion_date    DATE      NOT NULL,
  _ingestion_ts      TIMESTAMP NOT NULL,
  _batch_id          STRING    NOT NULL,
  _source_endpoint   STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (_ingestion_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 30 days',
  'quality'                          = 'bronze'
)
COMMENT 'Raw transfers from /transfers — append-only';

-- ── Ligas e cobertura ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS football_leagues_raw (
  payload            STRING    NOT NULL COMMENT 'JSON bruto do response /leagues',
  endpoint           STRING    NOT NULL,
  _ingestion_date    DATE      NOT NULL,
  _ingestion_ts      TIMESTAMP NOT NULL,
  _batch_id          STRING    NOT NULL,
  _source_endpoint   STRING    NOT NULL
)
USING DELTA
PARTITIONED BY (_ingestion_date)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'delta.logRetentionDuration'       = 'interval 30 days',
  'quality'                          = 'bronze'
)
COMMENT 'Raw league metadata from /leagues including coverage field — weekly refresh';

-- Verificação
SHOW TABLES IN mcp_platform.bronze;
