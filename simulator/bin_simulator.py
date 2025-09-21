import sys
import time
import json
import random
import threading
from datetime import datetime, timezone, timedelta
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable #type:ignore
from config import Config_File


class Bin_Simulator:
    def __init__(self):
        self.config = Config_File()
        self.stop_event = threading.Event()
        self.trigger_event = threading.Event()
        self.producer = None
        self.issue_type = None

    def get_kafka_producer(self, bootstrap_servers, retries=10, delay=5):
        """Retry logic for KafkaProducer connection"""
        for attempt in range(1, retries + 1):
            try:
                print(f"[INFO] Connecting to Kafka ({attempt}/{retries})...")
                return KafkaProducer(
                    bootstrap_servers=bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8")
                )
            except NoBrokersAvailable as e:
                print(f"[WARN] Kafka unavailable: {e}")
                time.sleep(delay)
        print("[ERROR] Kafka connection failed after retries. Exiting.")
        sys.exit(1)

    # Initialize Kafka producer
    def initialize_kafka_producer(self):
        self.producer = self.get_kafka_producer(self.config.KAFKA_BOOTSTRAP_SERVERS)
        # pass  # Commented out for data testing

    def generate_valid_record(self, bin_id):
        """Generates a valid smart bin record with random metadata each time"""
        return {
            "bin_id": bin_id,
            "latitude": round(random.uniform(*self.config.LATITUDE_RANGE), 6),
            "longitude": round(random.uniform(*self.config.LONGITUDE_RANGE), 6),
            "ward": random.choice(self.config.WARDS),
            "fill_level": random.randint(*self.config.FILL_LEVEL_RANGE),
            "temperature": round(random.uniform(*self.config.TEMPERATURE_RANGE), 1),
            "humidity": random.randint(*self.config.HUMIDITY_RANGE),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }

    def introduce_data_issues(self, record):
        """
        Introduces issues into a smart bin record using a dictionary-based approach
        for better scalability and readability.
        """
        self.issue_type = random.choice(self.config.ERROR_TYPES)
        now_utc = datetime.now(timezone.utc)

        # Dictionary mapping error types to a lambda function that applies the corruption
        error_actions = {
            # "null": lambda r: r.update({random.choice(["fill_level", "humidity", "temperature", "latitude", "longitude", "ward", "timestamp", "bin_id"]): None}),
            # "out_of_range": lambda r: r.update({
            #     random.choice(["fill_level", "humidity", "temperature"]): random.choice(
            #         [-1, 101, 150] if "fill_level" in r else [-20, 110] if "humidity" in r else [-60.0, 90.0]
            #     )
            # }),
            # "timestamp_skew": lambda r: r.update({"timestamp": (now_utc + timedelta(days=random.choice([-365, 365]))).isoformat().replace("+00:00", "Z")}),
            # "incomplete": lambda r: [r.pop(field, None) for field in random.sample([k for k in r if k != "bin_id"], min(3, len(r) - 1))],
            # "corrupted": lambda r: r.update({"fill_level": "high"}),
            
            "NULL_BIN_ID": lambda r: r.pop("bin_id", None),
            "INVALID_BIN_ID": lambda r: r.update({"bin_id": "invalid-format"}),
            "NULL_LATITUDE": lambda r: r.update({"latitude": None}),
            "INVALID_LATITUDE_RANGE": lambda r: r.update({"latitude": random.choice([-91.0, 91.0])}),
            "NON_NUMERIC_LATITUDE": lambda r: r.update({"latitude": "not_a_number"}),
            "NULL_LONGITUDE": lambda r: r.update({"longitude": None}),
            "INVALID_LONGITUDE_RANGE": lambda r: r.update({"longitude": random.choice([-181.0, 181.0])}),
            "NON_NUMERIC_LONGITUDE": lambda r: r.update({"longitude": "not_a_number"}),
            "NULL_WARD": lambda r: r.update({"ward": None}),
            "INVALID_WARD_NEGATIVE": lambda r: r.update({"ward": random.choice([-1, 0])}),
            "NON_INTEGER_WARD": lambda r: r.update({"ward": 2.5}),
            "NULL_FILL_LEVEL": lambda r: r.update({"fill_level": None}),
            "INVALID_FILL_LEVEL_RANGE": lambda r: r.update({"fill_level": random.choice([-1, 101])}),
            "NON_INTEGER_FILL_LEVEL": lambda r: r.update({"fill_level": 50.5}),
            "NULL_TEMPERATURE": lambda r: r.update({"temperature": None}),
            "INVALID_TEMPERATURE_RANGE": lambda r: r.update({"temperature": random.choice([-51.0, 81.0])}),
            "NON_NUMERIC_TEMPERATURE": lambda r: r.update({"temperature": "hot"}),
            "NULL_HUMIDITY": lambda r: r.update({"humidity": None}),
            "INVALID_HUMIDITY_RANGE": lambda r: r.update({"humidity": random.choice([-1, 101])}),
            "NON_NUMERIC_HUMIDITY": lambda r: r.update({"humidity": "humid"}),
            "NULL_TIMESTAMP": lambda r: r.update({"timestamp": None}),
            "MALFORMED_TIMESTAMP": lambda r: r.update({"timestamp": "2025-01-01 10:00:00"}),
            "FUTURE_TIMESTAMP": lambda r: r.update({"timestamp": (now_utc + timedelta(minutes=15)).isoformat().replace("+00:00", "Z")}),
            "OLD_TIMESTAMP": lambda r: r.update({"timestamp": (now_utc - timedelta(days=2)).isoformat().replace("+00:00", "Z")}),
            "NON_STRING_TIMESTAMP": lambda r: r.update({"timestamp": int(now_utc.timestamp())}),
        }

        # Execute the action if the issue type exists in the dictionary
        if self.issue_type in error_actions:
            error_actions[self.issue_type](record)
        
        return record

    def bin_worker(self, bin_id):
        """Thread function for generating bin data"""
        while not self.stop_event.is_set():
            try:
                record = self.generate_valid_record(bin_id)

                if random.random() < self.config.error_freq:
                    record = self.introduce_data_issues(record.copy())
                    topic = self.config.INVALID_TOPIC
                    print(f"[DEBUG] Invalid record for bin {bin_id} with issue introduced is {self.issue_type}.")
                    self.producer.send(topic, value=record)
                else:
                    topic = self.config.VALID_TOPIC
                    self.producer.send(topic, value=record)

                print(f"[{topic}] {json.dumps(record)}")

            except Exception as e:
                print(f"[ERROR] Bin {bin_id} error: {e}")
            time.sleep(self.config.DATA_INTERVAL_SECONDS)

    def main(self):
        print(f"\n[INFO] Starting Smart Bin Simulator with {len(self.config.BIN_IDS)} bins")
        print(f"[INFO] Sending data every {self.config.DATA_INTERVAL_SECONDS} seconds\n")

        threads = [
            threading.Thread(target=self.bin_worker, args=(bin_id,), daemon=True)
            for bin_id in self.config.BIN_IDS
        ]

        for thread in threads:
            thread.start()

        try:
            while not self.stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[INFO] Ctrl+C received. Shutting down...")
            self.stop_event.set()
        #wait for threads to finish
        for thread in threads:
            thread.join()
        self.producer.close()
        print("[INFO] Simulator stopped.")

if __name__ == "__main__":
    main_obj = Bin_Simulator()
    main_obj.initialize_kafka_producer()
    main_obj.main()
