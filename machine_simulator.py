import json
import time
import random
import paho.mqtt.client as mqtt

BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 1883
TOPIC = "acme/factory/sensors/node_1"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(BROKER_HOST, BROKER_PORT, 60)

print("Simulating Factory Node 1...")
print(f"Publishing JSON to '{TOPIC}'")
print("Press Ctrl+C to stop")

try:
    while True:
        payload = {
            "temp": round(75.0 + random.uniform(-5.0, 10.0), 2),
            "vib": round(2.5 + random.uniform(-1.0, 3.0), 3),
        }
        client.publish(TOPIC, json.dumps(payload))
        print(f"Published: {payload}")
        time.sleep(2)

except KeyboardInterrupt:
    print("\nSimulation stopped.")
    client.disconnect()
