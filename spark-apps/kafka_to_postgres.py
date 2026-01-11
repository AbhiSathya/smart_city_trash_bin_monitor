from pyspark.sql import SparkSession    # type: ignore
from pyspark.sql.functions import (     # type: ignore
    from_json, col, window, avg,
    lit, current_timestamp
)
from pyspark.sql.types import (         # type: ignore
    StructType, StructField, StringType,
    IntegerType, DoubleType, TimestampType
)
from pyspark.sql.functions import (     # type: ignore
    avg,
    max,
    min,
    approx_count_distinct,
    when,
    sum as spark_sum
)
from pyspark.sql.streaming import StreamingQueryListener    # type: ignore
import time
import psycopg2
from psycopg2.extras import execute_batch
from psycopg2 import OperationalError
from config import Config


# ----------------------------------------------------
# Query progress logger
# ----------------------------------------------------
class QueryProgressLogger(StreamingQueryListener):
    def onQueryStarted(self, event):
        print(f"🚀 Query started | id={event.id} | name={event.name}", flush=True)

    def onQueryProgress(self, event):
        p = event.progress
        duration = p.durationMs or {}
        print(
            f"""
            📊 Streaming Progress
            --------------------
            Batch ID        : {p.batchId}
            Input Rows      : {p.numInputRows}
            AddBatch Time   : {duration.get("addBatch", "N/A")} ms
            Trigger Time    : {duration.get("triggerExecution", "N/A")} ms
            Watermark       : {p.eventTime.get("watermark", "N/A") if p.eventTime else "N/A"}
            --------------------""",
            flush=True
        )
    def onQueryIdle(self, event):
        pass
        
    def onQueryTerminated(self, event):
        print(f"🛑 Query terminated | exception={event.exception}", flush=True)


# ----------------------------------------------------
# Main Streaming Job
# ----------------------------------------------------
class WardFillLevelStreamingJob:

    def __init__(self):
        self.spark = self._create_spark_session()
        self.schema = self._define_schema()
        self.checkpoint_path = "/opt/spark-checkpoints/ward_fill_level_aggregation_v1"
        self.dlq_checkpoint = "/opt/spark-checkpoints/dlq_invalid"

    # ------------------------------------------------
    # Spark Session
    # ------------------------------------------------
    def _create_spark_session(self) -> SparkSession:
        spark = (
            SparkSession.builder
            .appName("WardFillLevelAggregation")
            .config("spark.sql.shuffle.partitions", "2")
            .config("spark.default.parallelism", "2")
            .getOrCreate()
        )
        spark.conf.set("spark.sql.shuffle.partitions", "2")
        spark.sparkContext.setLogLevel("WARN")
        print("🚀 Spark session initialized")
        return spark

    # ------------------------------------------------
    # Schema
    # ------------------------------------------------
    def _define_schema(self) -> StructType:
        return StructType([
            StructField("schema_version", IntegerType(), True),
            StructField("bin_id", StringType(), True),
            StructField("latitude", DoubleType(), True),
            StructField("longitude", DoubleType(), True),
            StructField("ward", IntegerType(), True),
            StructField("fill_level", IntegerType(), True),
            StructField("temperature", DoubleType(), True),
            StructField("humidity", IntegerType(), True),
            StructField("timestamp", TimestampType(), True),
        ])


    # ------------------------------------------------
    # Kafka Source
    # ------------------------------------------------
    def read_from_kafka(self):
        print("📡 Connecting to Kafka")
        return (
            self.spark.readStream
            .format("kafka")
            .option("kafka.bootstrap.servers", Config.KAFKA_BOOTSTRAP)
            .option("subscribe", Config.VALID_TOPIC)
            .option("startingOffsets", "latest")
            .option("maxOffsetsPerTrigger", 500)
            .option("failOnDataLoss", "false")
            .load()
        )

    # ------------------------------------------------
    # Parse with DLQ
    # ------------------------------------------------
    def parse_with_dlq(self, kafka_df):
        raw_df = kafka_df.select(
            col("value").cast("string").alias("raw_value"),
            col("topic"),
            col("partition"),
            col("offset")
        )

        parsed_df = raw_df.withColumn(
            "data",
            from_json(col("raw_value"), self.schema)
        )

        valid_df = (
            parsed_df
            .filter(col("data").isNotNull())
            .select("data.*")
            .filter(col("timestamp").isNotNull())
            .withWatermark("timestamp", "2 minutes")
            .dropDuplicates(["bin_id", "timestamp"])
        )

        invalid_df = (
            parsed_df
            .filter(col("data").isNull())
            .withColumn("error_reason", lit("JSON_PARSE_FAILED"))
            .withColumn("error_time", current_timestamp())
        )

        return valid_df, invalid_df

    # ------------------------------------------------
    # DLQ Writer
    # ------------------------------------------------
    def start_dlq_stream(self, invalid_df):
        (
            invalid_df
            .selectExpr("to_json(struct(*)) AS value")
            .writeStream
            .format("kafka")
            .option("kafka.bootstrap.servers", Config.KAFKA_BOOTSTRAP)
            .option("topic", Config.INVALID_TOPIC)
            .option("checkpointLocation", Config.CHECKPOINT_DLQ)
            .start()
        )

    # ------------------------------------------------
    # Aggregation
    # ------------------------------------------------
    def aggregate(self, df):
        return (
            df.groupBy(
                window(col("timestamp"), "1 minute"),
                col("ward")
            )
            .agg(avg("fill_level").alias("avg_fill_level"))
            .select(
                col("ward"),
                col("window.start").alias("window_start"),
                col("window.end").alias("window_end"),
                col("avg_fill_level")
            )
        )
    
    def aggregate_risk_metrics(self, df):
        return (
            df.groupBy(
                window(col("timestamp"), "1 minute"),
                col("ward")
            )
            .agg(
                avg("fill_level").alias("avg_fill_level"),
                max("fill_level").alias("max_fill_level"),
                min("fill_level").alias("min_fill_level"),
                approx_count_distinct("bin_id").alias("total_bins"),
                spark_sum(
                    when(col("fill_level") >= 80, 1).otherwise(0)
                ).alias("bins_above_80")
            )
            .withColumn(
                "pct_bins_above_80",
                (col("bins_above_80") / col("total_bins")) * 100
            )
            .select(
                col("ward"),
                col("window.start").alias("window_start"),
                col("window.end").alias("window_end"),
                col("avg_fill_level"),
                col("max_fill_level"),
                col("min_fill_level"),
                col("total_bins"),
                col("bins_above_80"),
                col("pct_bins_above_80")
            )
        )


    # ------------------------------------------------
    # DB Retry Helper
    # ------------------------------------------------
    @staticmethod
    def with_db_retry(fn, retries=3, backoff=2):
        for attempt in range(1, retries + 1):
            try:
                return fn()
            except OperationalError:
                if attempt == retries:
                    raise
                sleep = backoff ** attempt
                print(f"⚠️ DB error, retrying in {sleep}s")
                time.sleep(sleep)

    # ------------------------------------------------
    # Safe foreachBatch wrapper
    # ------------------------------------------------
    @staticmethod
    def safe_foreach_batch(fn):
        def wrapper(df, batch_id):
            try:
                fn(df, batch_id)
            except Exception as e:
                print(f" Batch {batch_id} failed: {e}")
                raise
        return wrapper

    # ------------------------------------------------
    # PostgreSQL Sink
    # ------------------------------------------------
    @staticmethod
    def write_to_postgres(batch_df, batch_id):
        start = time.time()
        pdf = batch_df.toPandas()

        if pdf.empty:
            return

        rows = list(
            zip(
                pdf["ward"],
                pdf["window_start"],
                pdf["window_end"],
                pdf["avg_fill_level"]
            )
        )

        def db_write():
            conn = psycopg2.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                database=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                connect_timeout=5,
                options="-c statement_timeout=5000"
            )

            insert_sql = """
                INSERT INTO ward_fill_level_agg (
                    ward, window_start, window_end, avg_fill_level
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (ward, window_start, window_end)
                DO UPDATE SET avg_fill_level = EXCLUDED.avg_fill_level;
            """

            with conn:
                with conn.cursor() as cur:
                    execute_batch(cur, insert_sql, rows, page_size=500)

            conn.close()

        WardFillLevelStreamingJob.with_db_retry(db_write)

        print(f"✅ Batch {batch_id} committed in {round(time.time() - start, 2)}s")

    
    @staticmethod
    def write_risk_metrics_to_postgres(batch_df, batch_id):
        start = time.time()

        # Convert Spark DataFrame → Pandas (single action)
        pdf = batch_df.toPandas()

        if pdf.empty:
            print(f"⚠️ Risk batch {batch_id} empty — skipping")
            return

        rows = list(
            zip(
                pdf["ward"],
                pdf["window_start"],
                pdf["window_end"],
                pdf["avg_fill_level"],
                pdf["max_fill_level"],
                pdf["min_fill_level"],
                pdf["total_bins"],
                pdf["bins_above_80"],
                pdf["pct_bins_above_80"],
            )
        )

        def db_write():
            conn = psycopg2.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                database=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                connect_timeout=5,
                options="-c statement_timeout=5000"
            )

            insert_sql = """
                INSERT INTO ward_fill_level_risk_agg (
                    ward,
                    window_start,
                    window_end,
                    avg_fill_level,
                    max_fill_level,
                    min_fill_level,
                    total_bins,
                    bins_above_80,
                    pct_bins_above_80
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (ward, window_start, window_end)
                DO UPDATE SET
                    avg_fill_level = EXCLUDED.avg_fill_level,
                    max_fill_level = EXCLUDED.max_fill_level,
                    min_fill_level = EXCLUDED.min_fill_level,
                    total_bins = EXCLUDED.total_bins,
                    bins_above_80 = EXCLUDED.bins_above_80,
                    pct_bins_above_80 = EXCLUDED.pct_bins_above_80;
            """

            with conn:
                with conn.cursor() as cur:
                    execute_batch(cur, insert_sql, rows, page_size=500)

            conn.close()

        # Retry-safe DB write
        WardFillLevelStreamingJob.with_db_retry(db_write)

        print(
            f"✅ Risk batch {batch_id} committed "
            f"in {round(time.time() - start, 2)}s | rows={len(rows)}"
        )



    # ------------------------------------------------
    # Start Streaming
    # ------------------------------------------------
    def start(self):
        kafka_df = self.read_from_kafka()

        valid_df, invalid_df = self.parse_with_dlq(kafka_df)

        # Start DLQ stream
        self.start_dlq_stream(invalid_df)

        # -------------------------
        # Aggregation streams
        # -------------------------
        agg_df = self.aggregate(valid_df)
        risk_df = self.aggregate_risk_metrics(valid_df)

        self.spark.streams.addListener(QueryProgressLogger())

        # ---- Average aggregation stream ----
        avg_query = (
            agg_df.writeStream
            .queryName("ward_fill_level_aggregation")
            .trigger(processingTime=Config.TRIGGER_INTERVAL)
            .outputMode("update")
            .foreachBatch(
                WardFillLevelStreamingJob.safe_foreach_batch(
                    WardFillLevelStreamingJob.write_to_postgres
                )
            )
            .option("checkpointLocation", self.checkpoint_path)
            .start()
        )

        # ---- Risk aggregation stream ----
        risk_query = (
            risk_df.writeStream
            .queryName("ward_fill_level_risk_aggregation")
            .trigger(processingTime=Config.TRIGGER_INTERVAL)
            .outputMode("update")
            .foreachBatch(
                WardFillLevelStreamingJob.safe_foreach_batch(
                    WardFillLevelStreamingJob.write_risk_metrics_to_postgres
                )
            )
            .option(
                "checkpointLocation",
                "/opt/spark-checkpoints/ward_fill_level_risk_v1"
            )
            .start()
        )

        print("🚀 Both Spark streaming queries started")

        # Wait for any query to terminate
        self.spark.streams.awaitAnyTermination()




# ----------------------------------------------------
# Entry point
# ----------------------------------------------------
if __name__ == "__main__":
    WardFillLevelStreamingJob().start()
