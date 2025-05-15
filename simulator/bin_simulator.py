import sys
import time
import json
import random
import threading
from datetime import datetime, timezone, timedelta
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable # type: ignore
import config

stop_event = threading.Event()
trigger_event = threading.Event()

# Retry logic for KafkaProducer connection
def get_kafka_producer(bootstrap_servers, retries=10, delay=5):
    for attempt in range(1, retries + 1):
        try:
            print(f"[INFO] Attempting to connect to Kafka ({attempt}/{retries})...")
            producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
            )
            print("[INFO] Connected to Kafka successfully.")
            return producer
        except NoBrokersAvailable as e:
            print(f"[WARN] Kafka not available (attempt {attempt}): {e}")
            time.sleep(delay)
    print("[ERROR] Failed to connect to Kafka after multiple retries. Exiting.")
    sys.exit(1)

# Initialize Kafka producer with retry
producer = get_kafka_producer(config.KAFKA_BOOTSTRAP_SERVERS)

# Metadata for bins
bin_metadata = {
    bin_id: {
        "latitude": round(random.uniform(*config.LATITUDE_RANGE), 6),
        "longitude": round(random.uniform(*config.LONGITUDE_RANGE), 6),
        "ward": random.choice(config.WARDS)
    }
    for bin_id in config.BIN_IDS
}

last_valid_records = {}

def generate_valid_record(bin_id):
    meta = bin_metadata[bin_id]
    return {
        "bin_id": bin_id,
        "latitude": meta["latitude"],
        "longitude": meta["longitude"],
        "ward": meta["ward"],
        "fill_level": random.randint(*config.FILL_LEVEL_RANGE),
        "temperature": round(random.uniform(*config.TEMPERATURE_RANGE), 1),
        "humidity": random.randint(*config.HUMIDITY_RANGE),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }

def introduce_data_issues(record):
    issue_type = random.choice(config.ERROR_TYPES)

    if issue_type == "null":
        record[random.choice(["fill_level", "humidity", "temperature"])] = None
    elif issue_type == "out_of_range":
        field = random.choice(["fill_level", "humidity"])
        record[field] = 150 if field == "fill_level" else -20
    elif issue_type == "timestamp_skew":
        skew_days = random.choice([-365, 365])
        record["timestamp"] = (datetime.now(timezone.utc) + timedelta(days=skew_days)).isoformat().replace("+00:00", "Z")
    elif issue_type == "incomplete":
        for field in random.sample([k for k in record if k != "bin_id"], min(3, len(record) - 1)):
            record.pop(field, None)
    elif issue_type == "corrupted":
        record["fill_level"] = "high"

    return record

def bin_worker(bin_id):
    while not stop_event.is_set():
        if trigger_event.wait(timeout=1):
            try:
                record = generate_valid_record(bin_id)

                if random.random() < config.error_freq:
                    record = introduce_data_issues(record)
                    print(f"[DEBUG] Error introduced for bin {bin_id}")

                last_valid_records[bin_id] = record
                producer.send(config.KAFKA_TOPIC, value=record)
                print(json.dumps(record))  # For debug/logging

            except Exception as e:
                print(f"[ERROR] Bin {bin_id}: {e}")

            trigger_event.clear()

if __name__ == "__main__":
    print(f"[INFO] Starting Smart Bin Simulator with {len(config.BIN_IDS)} bins. Interval: {config.DATA_INTERVAL_SECONDS}s. Press Ctrl+C to stop.\n")

    threads = [
        threading.Thread(target=bin_worker, args=(bin_id,), daemon=True)
        for bin_id in config.BIN_IDS
    ]

    for thread in threads:
        thread.start()

    try:
        while not stop_event.is_set():
            trigger_event.set()
            time.sleep(0.5)
            print()
            time.sleep(config.DATA_INTERVAL_SECONDS - 0.5)
    except KeyboardInterrupt:
        print("\n[INFO] Ctrl+C received. Shutting down gracefully...")
        stop_event.set()

    time.sleep(1)
    producer.close()
    print("[INFO] Simulator stopped.")
