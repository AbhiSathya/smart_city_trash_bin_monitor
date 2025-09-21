import os
from dotenv import load_dotenv

class Config_File:
    def __init__(self):
        load_dotenv()
        
        # Kafka config
        self.KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.VALID_TOPIC = os.getenv("VALID_TOPIC", "valid-trash-bin-data")
        self.INVALID_TOPIC = os.getenv("INVALID_TOPIC", "invalid-trash-data")
        
        # Data simulator config
        self.DATA_INTERVAL_SECONDS = int(os.getenv("DATA_INTERVAL_SECONDS", "10"))
        self.error_freq = float(os.getenv("ERROR_FREQ", "0.2"))

        # Smart Bin Configuration 
        self.BIN_IDS = [f"B{str(i+1).zfill(3)}" for i in range(10)]
        self.WARDS = [1, 2, 3, 4, 5]

        # Latitude & Longitude Range (Temporary)
        self.LATITUDE_RANGE = (12.9500, 12.9900)
        self.LONGITUDE_RANGE = (77.5800, 77.6100)

        # Sensor Ranges
        self.FILL_LEVEL_RANGE = (0, 100)          # Percent
        self.TEMPERATURE_RANGE = (20.0, 40.0)     # °C
        self.HUMIDITY_RANGE = (30, 90)            # Percent

        # Error Types to Simulate
        self.ERROR_TYPES = [
            # "none",
            # "null",
            # "out_of_range",
            # "timestamp_skew",
            # "incomplete",
            # "corrupted",

            "NULL_BIN_ID",
            "INVALID_BIN_ID",
            # "DUPLICATE_BIN_ID",
            "NULL_LATITUDE",
            "INVALID_LATITUDE_RANGE",
            "NON_NUMERIC_LATITUDE",
            "NULL_LONGITUDE",
            "INVALID_LONGITUDE_RANGE",
            "NON_NUMERIC_LONGITUDE",
            "NULL_WARD",
            "INVALID_WARD_NEGATIVE",
            "NON_INTEGER_WARD",
            "NULL_FILL_LEVEL",
            "INVALID_FILL_LEVEL_RANGE",
            "NON_INTEGER_FILL_LEVEL",
            "NULL_TEMPERATURE",
            "INVALID_TEMPERATURE_RANGE",
            "NON_NUMERIC_TEMPERATURE",
            "NULL_HUMIDITY",
            "INVALID_HUMIDITY_RANGE",
            "NON_NUMERIC_HUMIDITY",
            "NULL_TIMESTAMP",
            "MALFORMED_TIMESTAMP",
            "FUTURE_TIMESTAMP",
            "OLD_TIMESTAMP",
            "NON_STRING_TIMESTAMP",
        ]
