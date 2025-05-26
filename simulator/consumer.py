from kafka import KafkaConsumer
import json

# Define the topic to consume from
TOPIC_NAME = 'raw-trash-bin-data'  # Replace with your topic name
KAFKA_BROKER = 'localhost:9092'  # Replace if your broker is hosted elsewhere

# Create Kafka consumer
consumer = KafkaConsumer(
    TOPIC_NAME,
    bootstrap_servers=[KAFKA_BROKER],
    auto_offset_reset='earliest',  # 'latest' to consume only new messages
    enable_auto_commit=True,
    group_id='my-consumer-group',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

print(f"Connected to Kafka. Listening to topic: {TOPIC_NAME}")

# Consume messages
try:
    for message in consumer:
        print(f"Received message: {message.value}")
except KeyboardInterrupt:
    print("\nConsumer stopped manually.")
finally:
    consumer.close()
