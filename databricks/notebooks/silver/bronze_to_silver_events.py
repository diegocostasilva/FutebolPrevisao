# Databricks notebook source
# MAGIC %md # Bronze → Silver: Events (gols, cartões, substituições)

import json
from datetime import datetime
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, IntegerType, StringType, StructField, StructType
from pyspark.sql.window import Window
from delta.tables import DeltaTable

dbutils.widgets.text("run_id", ""); dbutils.widgets.text("catalog", "football_prediction")
dbutils.widgets.text("ingestion_date", ""); dbutils.widgets.text("fixture_ids", "")

run_id = dbutils.widgets.get("run_id")
catalog = dbutils.widgets.get("catalog")
ingestion_date = dbutils.widgets.get("ingestion_date") or str(datetime.utcnow().date())

spark = SparkSession.builder.getOrCreate()
BRONZE = f"{catalog}.bronze.football_events_raw"
SILVER = f"{catalog}.silver.football_match_events"

event_schema = ArrayType(StructType([
    StructField("time", StructType([StructField("elapsed", IntegerType()), StructField("extra", IntegerType())])),
    StructField("team", StructType([StructField("id", IntegerType())])),
    StructField("player", StructType([StructField("id", IntegerType()), StructField("name", StringType())])),
    StructField("type", StringType()),
    StructField("detail", StringType()),
]))

raw_df = spark.table(BRONZE).filter(F.col("_ingestion_date") >= ingestion_date)
if raw_df.count() == 0:
    dbutils.notebook.exit(json.dumps({"rows_affected": 0, "status": "no_data"}))

df = raw_df.select(
    F.get_json_object("payload", "$.parameters.fixture").cast(IntegerType()).alias("fixture_id"),
    F.to_date(F.get_json_object("payload", "$.fixture.date")).alias("match_date"),
    F.from_json(F.get_json_object("payload", "$.response"), event_schema).alias("events"),
    F.col("_ingestion_ts"),
).filter(F.col("fixture_id").isNotNull())

df = (df.select("fixture_id", "match_date", "_ingestion_ts", F.explode_outer("events").alias("evt"))
      .select("fixture_id", "match_date", "_ingestion_ts",
              F.col("evt.team.id").alias("team_id"),
              F.col("evt.player.id").alias("player_id"),
              F.col("evt.player.name").alias("player_name"),
              F.col("evt.type").alias("event_type"),
              F.col("evt.detail").alias("event_detail"),
              F.col("evt.time.elapsed").alias("time_elapsed"),
              F.col("evt.time.extra").alias("time_extra")))

df = (df.drop("_ingestion_ts")
      .withColumn("_loaded_at", F.current_timestamp())
      .withColumn("_batch_id", F.lit(run_id)))

if DeltaTable.isDeltaTable(spark, SILVER):
    (DeltaTable.forName(spark, SILVER).alias("t")
     .merge(df.alias("s"),
            "t.fixture_id=s.fixture_id AND t.team_id=s.team_id AND t.time_elapsed=s.time_elapsed AND t.event_type=s.event_type")
     .whenMatchedUpdateAll().whenNotMatchedInsertAll().execute())
else:
    df.write.format("delta").mode("overwrite").saveAsTable(SILVER)

rows_affected = df.count()
spark.sql(f"OPTIMIZE {SILVER} ZORDER BY (fixture_id, team_id)")
dbutils.notebook.exit(json.dumps({"rows_affected": rows_affected, "status": "success"}))
