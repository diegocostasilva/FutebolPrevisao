# Databricks notebook source
# MAGIC %md
# MAGIC # Maintenance: OPTIMIZE + ZORDER + VACUUM
# MAGIC Executa manutenção Delta Lake em todas as tabelas Silver (e opcionalmente Gold).
# MAGIC Roda semanalmente via DatabricksOptimize Skill.

# COMMAND ----------

import json
from datetime import datetime

# COMMAND ----------
dbutils.widgets.text("run_id", "")
dbutils.widgets.text("catalog", "football_prediction")
dbutils.widgets.text("layer", "silver")   # silver | gold | all

run_id  = dbutils.widgets.get("run_id")
catalog = dbutils.widgets.get("catalog")
layer   = dbutils.widgets.get("layer") or "silver"

spark = SparkSession.builder.getOrCreate()

# COMMAND ----------
# Tabelas por camada — ZORDER BY colunas de alta cardinalidade usadas em filtros
SILVER_TABLES = [
    ("silver.football_fixtures",          "fixture_id, league_id"),
    ("silver.football_match_statistics",  "fixture_id, team_id"),
    ("silver.football_match_events",      "fixture_id, team_id"),
    ("silver.football_odds_prematch",     "fixture_id, bookmaker_id, bet_id"),
    ("silver.football_standings",         "league_id, season, team_id"),
    ("silver.football_lineups",           "fixture_id, team_id"),
    ("silver.football_players_stats",     "fixture_id, player_id"),
]

GOLD_TABLES = [
    ("gold.match_results",               "fixture_id, league_id"),
    ("gold.team_form",                   "team_id, league_id"),
    ("gold.head_to_head",                "home_team_id, away_team_id"),
    ("gold.league_standings_snapshot",   "league_id, season"),
    ("gold.player_performance",          "player_id, fixture_id"),
    ("gold.odds_movement",               "fixture_id, bookmaker_id"),
    ("gold.ml_features",                 "fixture_id"),
]

if layer == "silver":
    tables_to_optimize = SILVER_TABLES
elif layer == "gold":
    tables_to_optimize = GOLD_TABLES
else:
    tables_to_optimize = SILVER_TABLES + GOLD_TABLES

# COMMAND ----------
results = []
errors  = []

for table_suffix, zorder_cols in tables_to_optimize:
    full_table = f"{catalog}.{table_suffix}"
    try:
        # Verifica se tabela existe antes de otimizar
        spark.sql(f"DESCRIBE TABLE {full_table}")
        spark.sql(f"OPTIMIZE {full_table} ZORDER BY ({zorder_cols})")
        results.append(full_table)
        print(f"[OK] OPTIMIZE {full_table} ZORDER BY ({zorder_cols})")
    except Exception as e:
        msg = str(e)
        errors.append({"table": full_table, "error": msg})
        print(f"[SKIP] {full_table}: {msg}")

# COMMAND ----------
# VACUUM — apenas Silver (Bronze gerenciado separadamente, Gold retém 720h)
if layer in ("silver", "all"):
    vacuum_tables = SILVER_TABLES
    retain_hours  = 168   # 7 dias — mínimo recomendado para Silver
elif layer == "gold":
    vacuum_tables = GOLD_TABLES
    retain_hours  = 720   # 30 dias — Gold tem retenção maior
else:
    vacuum_tables = SILVER_TABLES + GOLD_TABLES
    retain_hours  = 168

for table_suffix, _ in vacuum_tables:
    full_table = f"{catalog}.{table_suffix}"
    try:
        spark.sql(f"VACUUM {full_table} RETAIN {retain_hours} HOURS")
        print(f"[OK] VACUUM {full_table} RETAIN {retain_hours}h")
    except Exception as e:
        print(f"[SKIP VACUUM] {full_table}: {e}")

# COMMAND ----------
summary = {
    "rows_affected": len(results),
    "optimized": results,
    "errors": errors,
    "layer": layer,
    "status": "success" if not errors else "partial",
}

dbutils.notebook.exit(json.dumps(summary))
