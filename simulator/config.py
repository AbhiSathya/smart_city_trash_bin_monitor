import os

# Kafka config
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "smart_bin_data")

# Data simulator config
error_freq = float(os.getenv("ERROR_FREQ") or "0.2")
DATA_INTERVAL_SECONDS = int(os.getenv("DATA_INTERVAL_SECONDS") or "10")

# Smart Bin Configuration
BIN_IDS = ["B001", "B002", "B003", "B004"]
WARDS = [1, 2, 3, 4, 5]

# Latitude & Longitude Range (Temporary)
LATITUDE_RANGE = (12.9500, 12.9900)
LONGITUDE_RANGE = (77.5800, 77.6100)

# Sensor Ranges
FILL_LEVEL_RANGE = (0, 100)          # Percent
TEMPERATURE_RANGE = (20.0, 40.0)     # °C
HUMIDITY_RANGE = (30, 90)            # Percent

# Error Types to Simulate
ERROR_TYPES = [
    "none",
    "null",
    "out_of_range",
    "duplicate",
    "timestamp_skew",
    "incomplete",
    "corrupted"
]
