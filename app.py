import os
import time
import json
import cv2
import pandas as pd
import numpy as np
import requests
import streamlit as st
from ultralytics import YOLO
import paho.mqtt.client as mqtt
import importlib.util
import av
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
from collections import deque

# Force Ultralytics to use a writable directory immediately
os.environ["YOLO_CONFIG_DIR"] = "/tmp/Ultralytics"

# 1. --- PAGE CONFIGURATION & SCADA CSS ---
st.set_page_config(page_title="ACME Sentinel | SCADA HMI", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    body { background-color: #050505; color: #e0e0e0; }
    .block-container { padding-top: 1rem !important; max-width: 98%; }
    header {visibility: hidden;}
    
    /* SCADA Hardware Metrics */
    div[data-testid="metric-container"] {
        background: #0a0a0a;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 2px;
        border-top: 3px solid #00ff41;
        box-shadow: inset 0 0 10px rgba(0,255,65,0.05);
        font-family: 'Courier New', monospace;
    }
    
    .terminal-box {
        background-color: #020202;
        color: #00ff41;
        font-family: 'Courier New', Courier, monospace;
        padding: 10px;
        border: 1px solid #333;
        height: 250px;
        overflow-y: hidden;
        font-size: 0.8rem;
        text-transform: uppercase;
    }
    
    .crit-alert { color: #ff3333; font-weight: bold; border-top: 3px solid #ff3333 !important; }
    hr { border-top: 1px solid #222; margin: 1rem 0; }
    </style>
""", unsafe_allow_html=True)

# 2. --- SYSTEM HEADER ---
st.markdown("<h2 style='font-family: monospace; color: #fff;'>ACME CORP // EDGE SENSOR INGESTION NODE</h2>", unsafe_allow_html=True)
st.caption("LIVE HARDWARE FEED: WEBRTC VISION | BROWSER MIC | MQTT JSON SENSORS")
st.divider()

# 3. --- THREAD-SAFE SENSOR BUFFER (EXPECTING JSON FROM REAL HARDWARE) ---
@st.cache_resource
def get_sensor_buffer():
    # Stores parsed JSON objects from physical sensors
    return deque(maxlen=50)

sensor_data = get_sensor_buffer()

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0: 
        client.subscribe("acme/factory/sensors/node_1")

def on_message(client, userdata, msg):
    try:
        # We now expect a real IoT JSON payload, e.g., {"temp": 45.2, "vib": 0.8, "pressure": 110}
        payload = json.loads(msg.payload.decode("utf-8"))
        payload["timestamp"] = time.strftime('%H:%M:%S')
        sensor_data.append(payload)
    except Exception:
        pass # Ignore malformed packets

@st.cache_resource
def get_mqtt_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, transport="websockets")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("broker.hivemq.com", 8000, 60)
    client.loop_start()
    return client

try:
    get_mqtt_client()
    mqtt_active = True
except Exception:
    mqtt_active = False

# 4. --- DASHBOARD GRID ---
vision_col, sensor_col, mic_col = st.columns([3, 2, 2], gap="small")

# --- COLUMN 1: LIVE PHYSICAL CAMERA (WEBRTC) ---
with vision_col:
    st.markdown("<h4 style='font-family: monospace;'>[ CH1: OPTICAL SENSOR ]</h4>", unsafe_allow_html=True)
    
    @st.cache_resource
    def load_model():
        return YOLO("yolov8n.pt")

    try:
        model = load_model()
        @st.cache_data
        def get_ice_servers():
            try:
                from twilio.rest import Client
                client = Client(st.secrets["TWILIO_ACCOUNT_SID"], st.secrets["TWILIO_AUTH_TOKEN"])
                return client.tokens.create().ice_servers
            except Exception:
                return [{"urls": ["stun:stun.l.google.com:19302"]}]

        def video_frame_callback(frame: av.VideoFrame) -> av.VideoFrame:
            img = frame.to_ndarray(format="bgr24")
            results = model.predict(img, conf=0.5, verbose=False)
            annotated = results[0].plot()
            
            # Simple SCADA HUD Overlay
            cv2.putText(annotated, f"ACME VIS-CORE // {time.strftime('%H:%M:%S')}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            return av.VideoFrame.from_ndarray(annotated, format="bgr24")

        webrtc_streamer(
            key="optical-feed",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTCConfiguration({"iceServers": get_ice_servers()}),
            video_frame_callback=video_frame_callback,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True,
        )
    except Exception as e:
        st.error("Optical Core Offline. Connect physical camera and grant permissions.")

# --- COLUMN 2: LIVE PHYSICAL SENSORS (MQTT) ---
with sensor_col:
    st.markdown("<h4 style='font-family: monospace;'>[ CH2: TELEMETRY I/O ]</h4>", unsafe_allow_html=True)
    
    @st.fragment(run_every=1)
    def render_sensors():
        if not mqtt_active:
            st.error("NETWORK FAULT: CANNOT REACH BROKER.")
            return

        if len(sensor_data) == 0:
            st.info("AWAITING HARDWARE SENSOR SYNC ON TOPIC: acme/factory/sensors/node_1")
            st.caption("Publish JSON to connect: {'temp': 0.0, 'vib': 0.0}")
            return

        latest = sensor_data[-1]
        t_val = latest.get("temp", 0.0)
        v_val = latest.get("vib", 0.0)

        # Dynamic metric rendering based on real hardware thresholds
        st.metric("Thermocouple (T-1)", f"{t_val:.1f} °C", "NOMINAL" if t_val < 80 else "OVERHEATING")
        st.metric("Piezo Vibration (V-1)", f"{v_val:.2f} mm/s", "STABLE" if v_val < 5.0 else "FATIGUE WARNING")

        # Plotting the hardware buffer
        df = pd.DataFrame(list(sensor_data))
        if 'temp' in df.columns:
            st.line_chart(df['temp'], height=150, use_container_width=True)

    render_sensors()

# --- COLUMN 3: LIVE PHYSICAL MICROPHONE (BROWSER API) ---
with mic_col:
    st.markdown("<h4 style='font-family: monospace;'>[ CH3: ACOUSTIC INGEST ]</h4>", unsafe_allow_html=True)
    st.caption("Record ambient machinery noise or dictate operator logs.")
    
    audio_value = st.audio_input("Initialize Acoustic Capture")
    
    st.markdown("<br><h4 style='font-family: monospace;'>[ ACOUSTIC ANALYSIS ]</h4>", unsafe_allow_html=True)
    sarvam_key = st.secrets.get("SARVAM_API_KEY", os.getenv("SARVAM_API_KEY", ""))
    
    if audio_value is not None:
        if not sarvam_key:
            st.error("AUTH ERR: SARVAM NEURAL ENGINE DISCONNECTED.")
        elif st.button("PROCESS ACOUSTIC VECTOR"):
            with st.spinner("ANALYZING AUDIO SIGNATURE..."):
                try:
                    response = requests.post(
                        "https://api.sarvam.ai/speech-to-text", 
                        headers={"api-subscription-key": sarvam_key}, 
                        files={"file": ("log.wav", audio_value.getvalue(), "audio/wav")}, 
                        timeout=60
                    )
                    if response.status_code == 200:
                        st.success("ACOUSTIC DECODE SUCCESS.")
                        st.markdown(f"<div class='terminal-box'>{response.json().get('transcript', '')}</div>", unsafe_allow_html=True)
                    else:
                        st.error(f"ENGINE FAULT: {response.status_code}")
                except Exception as e:
                    st.error(f"PACKET LOSS: {e}")

st.divider()