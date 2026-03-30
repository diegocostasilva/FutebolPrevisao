-- ============================================================
-- MCP Platform — PostgreSQL Serving Layer Initialization
-- Instance: postgres-serving (port 5433)
-- ============================================================

-- ── Schemas ─────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS serving;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS cache;

-- ── Roles ────────────────────────────────────────────────────
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mcp_reader') THEN
    CREATE ROLE mcp_reader;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mcp_writer') THEN
    CREATE ROLE mcp_writer;
  END IF;
END
$$;

GRANT USAGE ON SCHEMA serving, audit, cache TO mcp_reader;
GRANT USAGE ON SCHEMA serving, audit, cache, staging TO mcp_writer;
GRANT SELECT ON ALL TABLES IN SCHEMA serving TO mcp_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA audit TO mcp_reader;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA serving TO mcp_writer;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA audit TO mcp_writer;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA staging TO mcp_writer;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA cache TO mcp_writer;

ALTER DEFAULT PRIVILEGES IN SCHEMA serving GRANT SELECT ON TABLES TO mcp_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA serving GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO mcp_writer;
ALTER DEFAULT PRIVILEGES IN SCHEMA audit GRANT SELECT ON TABLES TO mcp_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA audit GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO mcp_writer;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO mcp_writer;
ALTER DEFAULT PRIVILEGES IN SCHEMA cache GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO mcp_writer;

-- ── Audit: pipeline_execution ─────────────────────────────────
CREATE TABLE IF NOT EXISTS audit.pipeline_execution (
    id              BIGSERIAL PRIMARY KEY,
    run_id          TEXT        NOT NULL,
    dag_id          TEXT        NOT NULL,
    task_id         TEXT        NOT NULL,
    agent_name      TEXT        NOT NULL,
    skill_name      TEXT        NOT NULL,
    skill_version   TEXT        NOT NULL,
    status          TEXT        NOT NULL CHECK (status IN ('running', 'success', 'failed', 'rolled_back')),
    rows_affected   BIGINT      DEFAULT 0,
    duration_ms     BIGINT,
    error_message   TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    metadata        JSONB       DEFAULT '{}'::JSONB
);

CREATE INDEX IF NOT EXISTS idx_pipeline_execution_run_id   ON audit.pipeline_execution (run_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_execution_dag_id   ON audit.pipeline_execution (dag_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_execution_status   ON audit.pipeline_execution (status);
CREATE INDEX IF NOT EXISTS idx_pipeline_execution_started  ON audit.pipeline_execution (started_at DESC);

COMMENT ON TABLE audit.pipeline_execution IS
  'Registry of every Skill execution across all pipeline runs. Written by every Agent via ServingAgent.';

-- ── Serving: placeholder for future serving tables ────────────
-- Tables in the serving schema are created by the ServingAgent
-- via postgres_upsert Skills during pipeline execution.

-- ── Cache: placeholder for materialized views ────────────────
-- Materialized views are created by the ServingAgent
-- and refreshed on schedule via the CacheInvalidator Skill.
