# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze → Silver: Odds Pré-Jogo
# MAGIC Normaliza odds de mercados (1X2, Over/Under, BTTS) da API-Football.
# MAGIC MERGE em Silver por (fixture_id, bookmaker_id, bet_id).

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
dbutils.widgets.text("fixture_ids", "")

run_id         = dbutils.widgets.get("run_id")
catalog        = dbutils.widgets.get("catalog")
ingestion_date = dbutils.widgets.get("ingestion_date") or str(datetime.utcnow().date())

spark = SparkSession.builder.getOrCreate()

# COMMAND ----------
BRONZE = f"{catalog}.bronze.football_odds_raw"
SILVER = f"{catalog}.silver.football_odds_prematch"

raw_df = spark.table(BRONZE).filter(F.col("_ingestion_date") >= ingestion_date)
count_raw = raw_df.count()
if count_raw == 0:
    dbutils.notebook.exit(json.dumps({"rows_affected": 0, "status": "no_data"}))

# COMMAND ----------
# Schemas aninhados da resposta da API-Football /odds
value_schema = StructType([
    StructField("value", StringType()),
    StructField("odd", StringType()),
])
bet_schema = StructType([
    StructField("id", IntegerType()),
    StructField("name", StringType()),
    StructField("values", ArrayType(value_schema)),
])
bookmaker_schema = StructType([
    StructField("id", IntegerType()),
    StructField("name", StringType()),
    StructField("bets", ArrayType(bet_schema)),
])
response_schema = StructType([
    StructField("fixture", StructType([StructField("id", IntegerType())])),
    StructField("bookmakers", ArrayType(bookmaker_schema)),
])

df_parsed = raw_df.select(
    F.get_json_object("payload", "$.parameters.fixture").cast(IntegerType()).alias("fixture_id"),
    F.to_date(F.get_json_object("payload", "$.fixture.date")).alias("match_date"),
    F.from_json(
        F.get_json_object("payload", "$.response"),
        ArrayType(response_schema),
    ).alias("responses"),
    F.col("_ingestion_ts"),
).filter(F.col("fixture_id").isNotNull())

# COMMAND ----------
# Explode: resposta → bookmaker → bet → value
df_bm = df_parsed.select(
    "fixture_id", "match_date", "_ingestion_ts",
    F.explode_outer("responses").alias("resp"),
).select(
    "fixture_id", "match_date", "_ingestion_ts",
    F.explode_outer("resp.bookmakers").alias("bm"),
).select(
    "fixture_id", "match_date", "_ingestion_ts",
    F.col("bm.id").alias("bookmaker_id"),
    F.col("bm.name").alias("bookmaker_name"),
    F.explode_outer("bm.bets").alias("bet"),
).select(
    "fixture_id", "match_date", "_ingestion_ts",
    "bookmaker_id", "bookmaker_name",
    F.col("bet.id").alias("bet_id"),
    F.col("bet.name").alias("bet_name"),
    F.explode_outer("bet.values").alias("val"),
).select(
    "fixture_id", "match_date", "_ingestion_ts",
    "bookmaker_id", "bookmaker_name",
    "bet_id", "bet_name",
    F.col("val.value").alias("outcome"),
    F.col("val.odd").cast(DoubleType()).alias("odd"),
)

# Dedup por chave (fixture_id, bookmaker_id, bet_id, outcome) — mais recente
window = Window.partitionBy("fixture_id", "bookmaker_id", "bet_id", "outcome").orderBy(
    F.col("_ingestion_ts").desc()
)
df_deduped = (
    df_bm.withColumn("_rn", F.row_number().over(window))
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
            "t.fixture_id = s.fixture_id AND t.bookmaker_id = s.bookmaker_id "
            "AND t.bet_id = s.bet_id AND t.outcome = s.outcome",
        )
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )
else:
    df_deduped.write.format("delta").mode("overwrite").saveAsTable(SILVER)

rows_affected = df_deduped.count()
spark.sql(f"OPTIMIZE {SILVER} ZORDER BY (fixture_id, bookmaker_id, bet_id)")

dbutils.notebook.exit(json.dumps({"rows_affected": rows_affected, "status": "success"}))
