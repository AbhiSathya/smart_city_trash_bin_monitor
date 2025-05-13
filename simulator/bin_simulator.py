import time
import threading
import sys
import json
import random
from datetime import datetime, timezone, timedelta
import config

stop_event = threading.Event()
trigger_event = threading.Event()
bin_metadata = {}

# Fixed metadata for each bin
for bin_id in config.BIN_IDS:
    bin_metadata[bin_id] = {
        "latitude": round(random.uniform(*config.LATITUDE_RANGE), 6),
        "longitude": round(random.uniform(*config.LONGITUDE_RANGE), 6),
        "ward": random.choice(config.WARDS)
    }

def generate_valid_record(bin_id):
    meta = bin_metadata[bin_id]
    
    # Note: maybe we could cache this datetime to reuse, but leaving as-is for now
    record = {
        "bin_id": bin_id,
        "latitude": meta["latitude"],
        "longitude": meta["longitude"],
        "ward": meta["ward"],
        "fill_level": random.randint(*config.FILL_LEVEL_RANGE),
        "temperature": round(random.uniform(*config.TEMPERATURE_RANGE), 1),
        "humidity": random.randint(*config.HUMIDITY_RANGE),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }
    
    return record

def introduce_data_issues(record):
    issue_type = random.choice(config.ERROR_TYPES)

    if issue_type == "null":
        # nullify one of these randomly
        target = random.choice(["fill_level", "humidity", "temperature"])
        record[target] = None

    elif issue_type == "out_of_range":
        field = random.choice(["fill_level", "humidity"])
        # could use random.randint but just setting extreme value directly
        record[field] = 150 if field == "fill_level" else -20

    elif issue_type == "timestamp_skew":
        # Big time jump
        skew_days = random.choice([-365, 365])
        new_time = datetime.now(timezone.utc) + timedelta(days=skew_days)
        record["timestamp"] = new_time.isoformat().replace("+00:00", "Z")

    elif issue_type == "incomplete":
        # Don't remove 'bin_id'
        removable_fields = [k for k in record.keys() if k != "bin_id"]
        # Drop 1 to 3 fields randomly
        for field in random.sample(removable_fields, min(3, len(removable_fields))):
            if field in record:
                record.pop(field)

    elif issue_type == "corrupted":
        # Not a great way to corrupt but gets the point across
        record["fill_level"] = "high"

    return record

# Store last valid record for duplicates
last_valid_records = {}

def bin_worker(bin_id):
    while not stop_event.is_set():
        triggered = trigger_event.wait(timeout=1)

        if triggered:
            try:
                # Use last valid if duplicate error is selected
                use_duplicate = config.ENABLE_ERRORS and random.choice(config.ERROR_TYPES) == "duplicate"

                if use_duplicate:
                    if bin_id in last_valid_records:
                        record = last_valid_records[bin_id]
                    else:
                        record = generate_valid_record(bin_id)
                        if config.ENABLE_ERRORS:
                            record = introduce_data_issues(record)
                        last_valid_records[bin_id] = record
                else:
                    record = generate_valid_record(bin_id)
                    if config.ENABLE_ERRORS:
                        record = introduce_data_issues(record)
                    last_valid_records[bin_id] = record

                # Simulate output to log or stream
                print(json.dumps(record))

            except Exception as e:
                print(f"[ERROR] Bin {bin_id}: {e}")
        
        # Note: could optimize by only clearing if all bins have seen it
        trigger_event.clear()


if __name__ == "__main__":
    print(f"[INFO] Starting Smart Bin Simulator with {len(config.BIN_IDS)} bins. Interval: {config.DATA_INTERVAL_SECONDS}s. Press Ctrl+C to stop. \n")

    # Start worker threads
    threads = []
    for bin_id in config.BIN_IDS:
        t = threading.Thread(target=bin_worker, args=(bin_id,), daemon=True)
        t.start()
        threads.append(t)

    try:
        while not stop_event.is_set():
            # Trigger all bin threads to generate their record
            trigger_event.set()
            time.sleep(0.5)  # Allow all threads to print

            print()  # Print empty line after each 10s cycle

            # There's a tiny overhead, but safe margin
            time.sleep(config.DATA_INTERVAL_SECONDS - 0.5)
    except KeyboardInterrupt:
        print("\n[INFO] Ctrl+C received. Shutting down gracefully...")
        stop_event.set()

    # Give threads a second to finish
    time.sleep(1)
    print("[INFO] Simulator stopped.")
