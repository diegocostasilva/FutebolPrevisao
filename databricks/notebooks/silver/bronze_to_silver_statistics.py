# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze → Silver: Statistics
# MAGIC Pivot do array {type, value} de estatísticas por time. MERGE em Silver.

# COMMAND ----------

import json
from datetime import datetime

from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType
from pyspark.sql.window import Window
from delta.tables import DeltaTable

# COMMAND ----------
dbutils.widgets.text("run_id", "")
dbutils.widgets.text("catalog", "football_prediction")
dbutils.widgets.text("ingestion_date", "")
dbutils.widgets.text("fixture_ids", "")

run_id         = dbutils.widgets.get("run_id")
catalog        = dbutils.widgets.get("catalog")
ingestion_date = dbutils.widgets.get("ingestion_date") or str(datetime.utcnow().date())

spark = SparkSession.builder.getOrCreate()
spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", "true")

# COMMAND ----------
BRONZE = f"{catalog}.bronze.football_statistics_raw"
SILVER = f"{catalog}.silver.football_match_statistics"

# Mapeamento tipo da API → coluna Silver
STAT_MAP = {
    "Shots on Goal": "shots_on_goal", "Shots off Goal": "shots_off_goal",
    "Total Shots": "total_shots", "Blocked Shots": "blocked_shots",
    "Shots insidebox": "shots_inside_box", "Shots outsidebox": "shots_outside_box",
    "Fouls": "fouls", "Corner Kicks": "corner_kicks", "Offsides": "offsides",
    "Ball Possession": "ball_possession", "Yellow Cards": "yellow_cards",
    "Red Cards": "red_cards", "Goalkeeper Saves": "goalkeeper_saves",
    "Total passes": "total_passes", "Passes accurate": "passes_accurate",
    "Passes %": "passes_pct", "expected_goals": "expected_goals",
}

raw_df = spark.table(BRONZE).filter(F.col("_ingestion_date") >= ingestion_date)
count_raw = raw_df.count()
if count_raw == 0:
    dbutils.notebook.exit(json.dumps({"rows_affected": 0, "status": "no_data"}))

# COMMAND ----------
# Explode por time e pivota estatísticas
from pyspark.sql.types import ArrayType, StringType, StructField, StructType

stats_schema = ArrayType(StructType([
    StructField("type", StringType()),
    StructField("value", StringType()),
]))
team_schema = ArrayType(StructType([
    StructField("team", StructType([StructField("id", IntegerType())])),
    StructField("statistics", stats_schema),
]))

df_parsed = raw_df.select(
    F.get_json_object("payload", "$.parameters.fixture").cast(IntegerType()).alias("fixture_id"),
    F.to_date(F.get_json_object("payload", "$.fixture.date")).alias("match_date"),
    F.from_json(F.get_json_object("payload", "$.response"), team_schema).alias("teams"),
    F.col("_ingestion_ts"),
).filter(F.col("fixture_id").isNotNull())

df_exploded = df_parsed.select(
    "fixture_id", "match_date", "_ingestion_ts",
    F.explode("teams").alias("team_data"),
).select(
    "fixture_id", "match_date", "_ingestion_ts",
    F.col("team_data.team.id").alias("team_id"),
    F.col("team_data.statistics").alias("stats"),
)

# Pivot: extrai cada stat pelo tipo
stat_cols = [
    F.filter("stats", lambda s: s["type"] == api_type).getItem(0)["value"]
    .cast(DoubleType()).alias(col_name)
    for api_type, col_name in STAT_MAP.items()
]

df_final = df_exploded.select("fixture_id", "match_date", "_ingestion_ts", "team_id", *stat_cols)

# Dedup por (fixture_id, team_id)
window = Window.partitionBy("fixture_id", "team_id").orderBy(F.col("_ingestion_ts").desc())
df_deduped = (
    df_final.withColumn("_rn", F.row_number().over(window))
    .filter(F.col("_rn") == 1)
    .drop("_rn", "_ingestion_ts")
    .withColumn("_loaded_at", F.current_timestamp())
    .withColumn("_batch_id", F.lit(run_id))
)

# COMMAND ----------
if DeltaTable.isDeltaTable(spark, SILVER):
    silver = DeltaTable.forName(spark, SILVER)
    (
        silver.alias("t")
        .merge(df_deduped.alias("s"), "t.fixture_id = s.fixture_id AND t.team_id = s.team_id")
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )
else:
    df_deduped.write.format("delta").mode("overwrite").saveAsTable(SILVER)

rows_affected = df_deduped.count()
spark.sql(f"OPTIMIZE {SILVER} ZORDER BY (fixture_id, team_id)")

dbutils.notebook.exit(json.dumps({"rows_affected": rows_affected, "status": "success"}))
