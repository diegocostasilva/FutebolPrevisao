-- ============================================================
-- 01_create_catalog.sql
-- Cria o catálogo mcp_platform e os schemas da arquitetura
-- Medallion (Bronze / Silver / Gold / Snapshots).
--
-- Executar como: admin do workspace Databricks
-- Warehouse: SQL Warehouse a15a748006670d03
-- ============================================================

-- Catálogo principal da plataforma
CREATE CATALOG IF NOT EXISTS mcp_platform
  COMMENT 'MCP Agent DAG Platform — Football Prediction Engine';

USE CATALOG mcp_platform;

-- Bronze: dados brutos vindos da API, append-only, schema-on-read
CREATE SCHEMA IF NOT EXISTS bronze
  COMMENT 'Raw data layer — JSON bruto da API-Football. Append-only. Retenção 30 dias.';

-- Silver: dados limpos, tipados e deduplicados via MERGE
CREATE SCHEMA IF NOT EXISTS silver
  COMMENT 'Cleaned & typed layer — flatten, dedup, MERGE upsert. Retenção 60 dias.';

-- Gold: marts prontos para consumo e features de ML
CREATE SCHEMA IF NOT EXISTS gold
  COMMENT 'Business-ready marts & ML features — idempotent overwrite/merge. Retenção 90 dias.';

-- Snapshots: SCD2 gerenciados pelo dbt
CREATE SCHEMA IF NOT EXISTS snapshots
  COMMENT 'dbt snapshots — SCD Type 2 para standings e team_strength.';

-- Verificação
SHOW SCHEMAS IN mcp_platform;
