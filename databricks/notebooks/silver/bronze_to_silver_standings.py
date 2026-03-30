# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze → Silver: Standings (Classificação)
# MAGIC Flatten da tabela de classificação por liga/temporada/time.
# MAGIC MERGE em Silver por (league_id, season, team_id).

# COMMAND ----------

import json
from datetime import datetime

from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, DoubleType, IntegerType, StringType, StructField, StructType
from pyspark.sql.window import Window
from delta.tables import DeltaTable

# COMMAND ----------
dbutils.widgets.text("run_id", "")
dbutils.widgets.text("catalog", "football_prediction")
dbutils.widgets.text("ingestion_date", "")
dbutils.widgets.text("league_ids", "")
dbutils.widgets.text("season", "")

run_id         = dbutils.widgets.get("run_id")
catalog        = dbutils.widgets.get("catalog")
ingestion_date = dbutils.widgets.get("ingestion_date") or str(datetime.utcnow().date())

spark = SparkSession.builder.getOrCreate()

# COMMAND ----------
BRONZE = f"{catalog}.bronze.football_standings_raw"
SILVER = f"{catalog}.silver.football_standings"

raw_df = spark.table(BRONZE).filter(F.col("_ingestion_date") >= ingestion_date)
count_raw = raw_df.count()
if count_raw == 0:
    dbutils.notebook.exit(json.dumps({"rows_affected": 0, "status": "no_data"}))

# COMMAND ----------
# Schema da resposta da API-Football /standings
all_schema = StructType([
    StructField("rank", IntegerType()),
    StructField("team", StructType([
        StructField("id", IntegerType()),
        StructField("name", StringType()),
    ])),
    StructField("points", IntegerType()),
    StructField("goalsDiff", IntegerType()),
    StructField("group", StringType()),
    StructField("form", StringType()),
    StructField("status", StringType()),
    StructField("description", StringType()),
    StructField("all", StructType([
        StructField("played", IntegerType()),
        StructField("win", IntegerType()),
        StructField("draw", IntegerType()),
        StructField("lose", IntegerType()),
        StructField("goals", StructType([
            StructField("for", IntegerType()),
            StructField("against", IntegerType()),
        ])),
    ])),
])

league_schema = StructType([
    StructField("id", IntegerType()),
    StructField("name", StringType()),
    StructField("season", IntegerType()),
    StructField("standings", ArrayType(ArrayType(all_schema))),
])

response_schema = ArrayType(StructType([
    StructField("league", league_schema),
]))

df_parsed = raw_df.select(
    F.from_json(F.get_json_object("payload", "$.response"), response_schema).alias("responses"),
    F.col("_ingestion_ts"),
)

# COMMAND ----------
# Explode: response → league → standings (array de arrays) → time
df_league = df_parsed.select(
    "_ingestion_ts",
    F.explode_outer("responses").alias("resp"),
).select(
    "_ingestion_ts",
    F.col("resp.league.id").alias("league_id"),
    F.col("resp.league.name").alias("league_name"),
    F.col("resp.league.season").alias("season"),
    F.explode_outer("resp.league.standings").alias("group_standings"),
).select(
    "_ingestion_ts", "league_id", "league_name", "season",
    F.explode_outer("group_standings").alias("entry"),
).select(
    "_ingestion_ts", "league_id", "league_name", "season",
    F.col("entry.rank").alias("rank"),
    F.col("entry.team.id").alias("team_id"),
    F.col("entry.team.name").alias("team_name"),
    F.col("entry.points").alias("points"),
    F.col("entry.goalsDiff").alias("goal_diff"),
    F.col("entry.group").alias("group"),
    F.col("entry.form").alias("form"),
    F.col("entry.status").alias("status"),
    F.col("entry.description").alias("description"),
    F.col("entry.all.played").alias("played"),
    F.col("entry.all.win").alias("wins"),
    F.col("entry.all.draw").alias("draws"),
    F.col("entry.all.lose").alias("losses"),
    F.col("entry.all.goals.for").alias("goals_for"),
    F.col("entry.all.goals.against").alias("goals_against"),
).filter(F.col("league_id").isNotNull() & F.col("team_id").isNotNull())

# Dedup por (league_id, season, team_id) — mais recente
window = Window.partitionBy("league_id", "season", "team_id").orderBy(F.col("_ingestion_ts").desc())
df_deduped = (
    df_league.withColumn("_rn", F.row_number().over(window))
    .filter(F.col("_rn") == 1)
    .drop("_rn", "_ingestion_ts")
    .withColumn("_loaded_at", F.current_timestamp())
    .withColumn("_batch_id", F.lit(run_id))
)

# COMMAND ----------
if DeltaTable.isDeltaTable(spark, SILVER):
    (
        DeltaTable.forName(spark, SILVER).alias("t")
        .merge(
            df_deduped.alias("s"),
            "t.league_id = s.league_id AND t.season = s.season AND t.team_id = s.team_id",
        )
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )
else:
    df_deduped.write.format("delta").mode("overwrite").saveAsTable(SILVER)

rows_affected = df_deduped.count()
spark.sql(f"OPTIMIZE {SILVER} ZORDER BY (league_id, season, team_id)")

dbutils.notebook.exit(json.dumps({"rows_affected": rows_affected, "status": "success"}))
