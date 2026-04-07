import time
import random
import paho.mqtt.client as mqtt

# Connect to the exact same public broker as your dashboard
client = mqtt.Client()
client.connect("broker.hivemq.com", 1883, 60)

print("⚙️  Simulating CNC Machine A...")
print("📡 Publishing temperature data to 'factory/machine_a/temp'")
print("🛑 Press Ctrl+C to stop")

try:
    while True:
        # Generate a realistic operating temperature (e.g., around 75°C)
        base_temp = 75.0
        fluctuation = random.uniform(-5.0, 5.0)
        current_temp = round(base_temp + fluctuation, 2)
        
        # Publish the data to the MQTT topic
        client.publish("factory/machine_a/temp", current_temp)
        print(f"Published: {current_temp}°C")
        
        # Wait for 2 seconds before sending the next reading
        time.sleep(2)

except KeyboardInterrupt:
    print("\nMachine Simulation Stopped.")
    client.disconnect()