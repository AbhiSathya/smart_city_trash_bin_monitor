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
import psycopg2
from psycopg2.extras import execute_batch



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
        if batch_df.rdd.isEmpty():
            print(f"⚠️ Batch {batch_id} is empty — skipping")
            return

        print(f"📝 UPSERT batch {batch_id}")

        rows = [
            (
                row.ward,
                row.window_start,
                row.window_end,
                row.avg_fill_level
            )
            for row in batch_df.collect()
        ]

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

        with conn:
            with conn.cursor() as cur:
                execute_batch(cur, insert_sql, rows, page_size=100)

        conn.close()

    # ----------------------------------------------------
    # Start streaming
    # ----------------------------------------------------
    def start(self):
        kafka_df = self.read_from_kafka()
        clean_df = self.parse_and_deduplicate(kafka_df)
        agg_df = self.aggregate(clean_df)

        query = (
            agg_df.writeStream
            .queryName("ward_fill_level_aggregation")
            .outputMode("update")
            .foreachBatch(self.write_to_postgres)
            .option("checkpointLocation", self.checkpoint_path)
            .start()
        )

        print("✅ Streaming query started", flush=True)
        query.awaitTermination()


# ----------------------------------------------------
# Entry point
# ----------------------------------------------------
if __name__ == "__main__":
    job = WardFillLevelStreamingJob()
    job.start()
