import streamlit as st
import pandas as pd
import numpy as np
import time
import cv2
import requests
from ultralytics import YOLO
import paho.mqtt.client as mqtt

# 1. --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Factory Command Center", layout="wide")

st.title("🏭 Automated Shop-Floor Command Center")
st.markdown("Real-time monitoring for machine status and production metrics.")

# 2. --- TOP-LEVEL METRICS ---
col1, col2, col3 = st.columns(3)
col1.metric("Spindle Temperature", "72°C", "1.2°C")
col2.metric("Parts Produced", "1,240", "15")
col3.metric("Overall Equipment Effectiveness (OEE)", "88%", "2%")

st.divider()

# 3. --- AI-ENABLED CAMERA SECTION ---
st.subheader("📹 Live Floor Monitoring (AI Enabled)")
st.caption("Simulated RTSP stream with real-time object detection")

# Load the lightweight YOLOv8 model
@st.cache_resource
def load_model():
    return YOLO("yolov8n.pt")

model = load_model()

# Checkbox to trigger the camera loop
run_camera = st.checkbox("Turn on Camera Feed (Note: Pauses auto-refresh while active)")
FRAME_WINDOW = st.image([])

if run_camera:
    camera = cv2.VideoCapture(0)
    while run_camera:
        success, frame = camera.read()
        if success:
            # Pass the frame to the YOLO model 
            results = model.predict(frame, conf=0.4) 
            # Plot the bounding boxes onto the frame
            annotated_frame = results[0].plot()
            # Convert BGR to RGB
            annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            # Display the AI-processed frame
            FRAME_WINDOW.image(annotated_frame)
else:
    st.write("Camera is offline.")

st.divider()

# 4. --- LIVE MACHINE DATA & ALERTS (REAL MQTT) ---
st.subheader("📈 Live Machine Data Feed")
st.caption("Connected to HiveMQ Public Broker - Topic: factory/machine_a/temp")

# Initialize session state to store our machine data
if 'machine_data' not in st.session_state:
    st.session_state['machine_data'] = []

# Define MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    client.subscribe("factory/machine_a/temp")

def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8")
    try:
        temp_value = float(payload)
        st.session_state['machine_data'].append(temp_value)
        # Keep only the last 20 data points
        if len(st.session_state['machine_data']) > 20:
            st.session_state['machine_data'].pop(0)
    except ValueError:
        pass

# Setup the MQTT Client
@st.cache_resource
def get_mqtt_client():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("broker.hivemq.com", 1883, 60)
    client.loop_start()
    return client

get_mqtt_client()

# --- ALERT LOGIC & CHART DISPLAY ---
if len(st.session_state['machine_data']) > 0:
    # Get the most recent temperature reading
    latest_temp = st.session_state['machine_data'][-1]
    
    # Check if it crosses our safety thresholds
    if latest_temp > 78.0:
        st.error(f"🚨 CRITICAL WARNING: Spindle Temperature Overheating at {latest_temp}°C!")
    elif latest_temp > 76.0:
        st.warning(f"⚠️ CAUTION: Temperature rising ({latest_temp}°C). Monitor closely.")
    else:
        st.success(f"✅ Machine operating normally at {latest_temp}°C.")

    # Display the chart
    df = pd.DataFrame(st.session_state['machine_data'], columns=['Machine A Temp (°C)'])
    st.line_chart(df)
else:
    st.info("Waiting for machine data... Start the simulator script to see data here.")

st.divider()

# 5. --- SARVAM AI AUDIO SECTION ---
st.subheader("🎙️ Voice-Activated Maintenance Logging")
st.caption("Powered by Sarvam AI - Speak your maintenance notes naturally")

# Streamlit's built-in audio recorder
audio_value = st.audio_input("Click to record a maintenance log")

if audio_value is not None:
    if st.button("Transcribe Log with Sarvam AI"):
        with st.spinner("Processing audio..."):
            
            # Sarvam API endpoint
            url = "https://api.sarvam.ai/speech-to-text"
            
            # Be sure to add your API Key here!
            headers = {
                "api-subscription-key": "sk_ry4d2q1k_zmcLaq0SA9AgXUEvbrW28gdG"
            }
            
            files = {
                "file": ("log.wav", audio_value, "audio/wav")
            }
            
            try:
                response = requests.post(url, headers=headers, files=files)
                
                if response.status_code == 200:
                    transcript = response.json().get("transcript", "No transcript found.")
                    st.success("Log Transcribed Successfully!")
                    st.text_area("Digital Log Entry:", value=transcript, height=100)
                else:
                    st.error(f"API Error: {response.status_code} - {response.text}")
                    
            except Exception as e:
                st.error(f"Failed to connect to Sarvam AI: {e}")

# 6. --- AUTO REFRESH LOOP ---
# This forces the page to continually update the MQTT chart, 
# but we pause it while the camera is actively running so the video doesn't glitch.
if not run_camera:
    time.sleep(1)
    st.rerun()