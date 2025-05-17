import os
from dotenv import load_dotenv

load_dotenv()

# Kafka config
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
VALID_TOPIC = os.getenv("VALID_TOPIC", "valid-trash-bin-data")
INVALID_TOPIC = os.getenv("INVALID_TOPIC", "invalid-trash-data")

# Data simulator config
DATA_INTERVAL_SECONDS = int(os.getenv("DATA_INTERVAL_SECONDS", "10"))
error_freq = float(os.getenv("ERROR_FREQ", "0.2"))

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
