from pyspark.sql import SparkSession  # type: ignore
from pyspark.sql.functions import (  # type: ignore
    from_json,
    col,
    window,
    avg
)
from pyspark.sql.types import (  # type: ignore
    StructType,
    StructField,
    StringType,
    IntegerType,
    DoubleType,
    TimestampType
)
import time
import psycopg2
from psycopg2.extras import execute_batch
from pyspark.sql.streaming import StreamingQueryListener  # type: ignore


class QueryProgressLogger(StreamingQueryListener):

    def onQueryStarted(self, event):
        print(
            f"🚀 Query started | id={event.id} | name={event.name}",
            flush=True
        )

    def onQueryProgress(self, event):
        p = event.progress

        # ---------- basic metrics ----------
        batch_id = p.batchId
        input_rows = p.numInputRows

        duration = p.durationMs or {}
        add_batch_time = duration.get("addBatch", "N/A")
        trigger_time = duration.get("triggerExecution", "N/A")

        # ---------- watermark ----------
        watermark = "N/A"
        if p.eventTime:
            watermark = p.eventTime.get("watermark", "N/A")

        # ---------- state store ----------
        state_rows = 0
        state_mem = 0

        if p.stateOperators:
            state = p.stateOperators[0]
            state_rows = getattr(state, "numRowsTotal", 0)
            state_mem = getattr(state, "memoryUsedBytes", 0)

        print(
            f"""
                📊 Streaming Progress
                --------------------
                Batch ID        : {batch_id}
                Input Rows      : {input_rows}
                AddBatch Time   : {add_batch_time} ms
                Trigger Time    : {trigger_time} ms
                Watermark       : {watermark}
                State Rows      : {state_rows}
                State Memory    : {state_mem / 1024 / 1024:.2f} MB
            """,
            flush=True
        )

    def onQueryIdle(self, event):
        # Normal when no Kafka data arrives
        pass

    def onQueryTerminated(self, event):
        print(
            f"🛑 Query terminated | id={event.id} | exception={event.exception}",
            flush=True
        )


class WardFillLevelStreamingJob:
    """
    Spark Structured Streaming job for
    Kafka -> Aggregation -> PostgreSQL
    """

    def __init__(self):
        self.spark = self._create_spark_session()
        self.schema = self._define_schema()

        # SINGLE SOURCE OF TRUTH
        self.checkpoint_path = "/opt/spark-checkpoints/ward_fill_level_aggregation_v1"

    # ----------------------------------------------------
    # Spark session
    # ----------------------------------------------------
    def _create_spark_session(self) -> SparkSession:
        spark = (
            SparkSession.builder
            .appName("WardFillLevelAggregation")
            .getOrCreate()
        )
        spark.sparkContext.setLogLevel("WARN")
        print("🚀 Spark session initialized")
        return spark

    # ----------------------------------------------------
    # Schema
    # ----------------------------------------------------
    def _define_schema(self) -> StructType:
        return StructType([
            StructField("bin_id", StringType(), True),
            StructField("latitude", DoubleType(), True),
            StructField("longitude", DoubleType(), True),
            StructField("ward", IntegerType(), True),
            StructField("fill_level", IntegerType(), True),
            StructField("temperature", DoubleType(), True),
            StructField("humidity", IntegerType(), True),
            StructField("timestamp", TimestampType(), True),
        ])

    # ----------------------------------------------------
    # Kafka Source
    # ----------------------------------------------------
    def read_from_kafka(self):
        print("📡 Connecting to Kafka")
        return (
            self.spark.readStream
            .format("kafka")
            .option("kafka.bootstrap.servers", "kafka:9092")
            .option("subscribe", "valid-trash-bin-data")
            .option("startingOffsets", "latest")
            .option("maxOffsetsPerTrigger", 500)
            .option("failOnDataLoss", "false")
            .load()
        )

    # ----------------------------------------------------
    # Parse & deduplicate
    # ----------------------------------------------------
    def parse_and_deduplicate(self, kafka_df):
        parsed_df = (
            kafka_df
            .select(from_json(col("value").cast("string"), self.schema).alias("data"))
            .select("data.*")
            .filter(col("timestamp").isNotNull())
        )

        dedup_df = (
            parsed_df
            .withWatermark("timestamp", "2 minutes")
            .dropDuplicates(["bin_id", "timestamp"])
        )

        print("🧹 Deduplication enabled")
        return dedup_df

    # ----------------------------------------------------
    # Aggregation
    # ----------------------------------------------------
    def aggregate(self, df):
        return (
            df.groupBy(
                window(col("timestamp"), "1 minute"),
                col("ward")
            )
            .agg(
                avg("fill_level").alias("avg_fill_level")
            )
            .select(
                col("ward"),
                col("window.start").alias("window_start"),
                col("window.end").alias("window_end"),
                col("avg_fill_level")
            )
        )

    # ----------------------------------------------------
    # PostgreSQL Sink
    # ----------------------------------------------------
    @staticmethod
    def write_to_postgres(batch_df, batch_id: int):
        start_time = time.time()

        row_count = batch_df.count()
        if row_count == 0:
            print(f"⚠️ Batch {batch_id} is empty — skipping")
            return

        print(f"📝 UPSERT batch {batch_id} | rows={row_count}")

        # Convert Spark rows → Python tuples
        rows = [
            (
                row.ward,
                row.window_start,
                row.window_end,
                row.avg_fill_level
            )
            for row in batch_df.toLocalIterator()
        ]

        # PostgreSQL connection
        conn = psycopg2.connect(
            host="postgres",
            port=5432,
            database="trash_bin_db",
            user="admin",
            password="admin"
        )

        insert_sql = """
            INSERT INTO ward_fill_level_agg (
                ward,
                window_start,
                window_end,
                avg_fill_level
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (ward, window_start, window_end)
            DO UPDATE SET
                avg_fill_level = EXCLUDED.avg_fill_level;
        """

        # UPSERT in batches (efficient + idempotent)
        with conn:
            with conn.cursor() as cur:
                execute_batch(
                    cur,
                    insert_sql,
                    rows,
                    page_size=500
                )

        conn.close()

        duration = round(time.time() - start_time, 2)
        print(f"✅ Batch {batch_id} committed in {duration}s")

    # ----------------------------------------------------
    # Start streaming
    # ----------------------------------------------------
    def start(self):
        kafka_df = self.read_from_kafka()
        clean_df = self.parse_and_deduplicate(kafka_df)
        agg_df = self.aggregate(clean_df)

        # Register progress listener
        self.spark.streams.addListener(QueryProgressLogger())

        # Start streaming query
        query = (
            agg_df.writeStream
            .queryName("ward_fill_level_aggregation")
            .trigger(processingTime="30 seconds")
            .outputMode("update")
            .foreachBatch(self.write_to_postgres)
            .option("checkpointLocation", self.checkpoint_path)
            .start()
        )

        print("✅ Streaming query started", flush=True)

        # Block until terminated
        query.awaitTermination()



# ----------------------------------------------------
# Entry point
# ----------------------------------------------------
if __name__ == "__main__":
    job = WardFillLevelStreamingJob()
    job.start()
