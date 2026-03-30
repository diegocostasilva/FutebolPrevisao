# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze → Silver: Fixtures
# MAGIC Flatten do JSON bruto de fixtures, extração de campos tipados, MERGE em Silver.

# COMMAND ----------

import json
from datetime import datetime

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import IntegerType
from pyspark.sql.window import Window
from delta.tables import DeltaTable

# COMMAND ----------
# Parâmetros (injetados pelo Databricks Jobs SDK)
dbutils.widgets.text("run_id", "")
dbutils.widgets.text("execution_date", "")
dbutils.widgets.text("catalog", "football_prediction")
dbutils.widgets.text("league_ids", "71")
dbutils.widgets.text("season", "2025")
dbutils.widgets.text("mode", "incremental")
dbutils.widgets.text("ingestion_date", "")

run_id        = dbutils.widgets.get("run_id")
catalog       = dbutils.widgets.get("catalog")
season        = int(dbutils.widgets.get("season"))
ingestion_date = dbutils.widgets.get("ingestion_date") or str(datetime.utcnow().date())

spark = SparkSession.builder.getOrCreate()

print(f"run_id={run_id} | catalog={catalog} | ingestion_date={ingestion_date}")

# COMMAND ----------
BRONZE = f"{catalog}.bronze.football_fixtures_raw"
SILVER = f"{catalog}.silver.football_fixtures"

raw_df = spark.table(BRONZE).filter(F.col("_ingestion_date") >= ingestion_date)
count_raw = raw_df.count()
print(f"Registros Bronze lidos: {count_raw}")

if count_raw == 0:
    dbutils.notebook.exit(json.dumps({"rows_affected": 0, "status": "no_data"}))

# COMMAND ----------
# Parse e extração de campos tipados
df = raw_df.select(
    F.get_json_object("payload", "$.fixture.id").cast(IntegerType()).alias("fixture_id"),
    F.get_json_object("payload", "$.league.id").cast(IntegerType()).alias("league_id"),
    F.get_json_object("payload", "$.league.name").alias("league_name"),
    F.get_json_object("payload", "$.league.season").cast(IntegerType()).alias("season"),
    F.to_date(F.get_json_object("payload", "$.fixture.date")).alias("match_date"),
    F.to_timestamp(F.get_json_object("payload", "$.fixture.date")).alias("match_ts"),
    F.get_json_object("payload", "$.teams.home.id").cast(IntegerType()).alias("home_team_id"),
    F.get_json_object("payload", "$.teams.home.name").alias("home_team_name"),
    F.get_json_object("payload", "$.teams.away.id").cast(IntegerType()).alias("away_team_id"),
    F.get_json_object("payload", "$.teams.away.name").alias("away_team_name"),
    F.get_json_object("payload", "$.goals.home").cast(IntegerType()).alias("goals_home"),
    F.get_json_object("payload", "$.goals.away").cast(IntegerType()).alias("goals_away"),
    F.get_json_object("payload", "$.fixture.status.short").alias("status"),
    F.get_json_object("payload", "$.fixture.venue.name").alias("venue"),
    F.get_json_object("payload", "$.fixture.referee").alias("referee"),
    F.get_json_object("payload", "$.league.round").alias("round"),
    F.col("_ingestion_ts"),
).filter(F.col("fixture_id").isNotNull())

# Resultado: H / D / A (apenas para status FT)
df = df.withColumn(
    "result",
    F.when(
        F.col("status") == "FT",
        F.when(F.col("goals_home") > F.col("goals_away"), F.lit("H"))
        .when(F.col("goals_home") == F.col("goals_away"), F.lit("D"))
        .otherwise(F.lit("A")),
    ).otherwise(F.lit(None).cast("string")),
)

# Deduplicar por fixture_id — manter mais recente
window = Window.partitionBy("fixture_id").orderBy(F.col("_ingestion_ts").desc())
df = (
    df.withColumn("_rn", F.row_number().over(window))
    .filter(F.col("_rn") == 1)
    .drop("_rn", "_ingestion_ts")
    .withColumn("_loaded_at", F.current_timestamp())
    .withColumn("_batch_id", F.lit(run_id))
)

# COMMAND ----------
# MERGE upsert em Silver
if DeltaTable.isDeltaTable(spark, SILVER):
    silver = DeltaTable.forName(spark, SILVER)
    (
        silver.alias("t")
        .merge(df.alias("s"), "t.fixture_id = s.fixture_id")
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )
else:
    df.write.format("delta").mode("overwrite").saveAsTable(SILVER)

rows_affected = df.count()

# COMMAND ----------
# OPTIMIZE + ZORDER
spark.sql(f"OPTIMIZE {SILVER} ZORDER BY (fixture_id, league_id)")
print(f"OPTIMIZE concluído. rows_affected={rows_affected}")

# COMMAND ----------
# Retorna métricas para a Skill (DatabricksJobBaseSkill._extract_rows_from_output)
dbutils.notebook.exit(json.dumps({"rows_affected": rows_affected, "status": "success"}))
