import os
import time
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

# 1. --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Factory Command Center", layout="wide")

st.title("🏭 Automated Shop-Floor Command Center")
st.markdown("Real-time monitoring for machine status and production metrics.")

cv2_available = importlib.util.find_spec("cv2") is not None

def get_cv2_module():
    if not cv2_available:
        return None
    return importlib.import_module("cv2")

# 2. --- TOP-LEVEL METRICS ---
col1, col2, col3 = st.columns(3)
col1.metric("Spindle Temperature", "72°C", "1.2°C")
col2.metric("Parts Produced", "1,240", "15")
col3.metric("Overall Equipment Effectiveness (OEE)", "88%", "2%")

st.divider()

# 3. --- AI-ENABLED CAMERA SECTION ---
st.subheader("📹 Floor Monitoring (AI Enabled)")
st.caption("Live browser streaming (WebRTC) or static image upload.")

@st.cache_resource
def load_model():
    return YOLO("yolov8n.pt")

try:
    model = load_model()
    model_ready = True
except Exception as e:
    model = None
    model_ready = False
    st.error(f"Could not load YOLO model: {e}")

if model_ready:
    input_mode = st.radio("Select Vision Mode", ["Live Cloud Video (WebRTC)", "Static Image Upload"])

    if input_mode == "Live Cloud Video (WebRTC)":
        # Dynamic ICE server fetching for NAT traversal (Requires Twilio for production)
        @st.cache_data
        def get_ice_servers():
            try:
                from twilio.rest import Client
                twilio_sid = st.secrets["TWILIO_ACCOUNT_SID"]
                twilio_token = st.secrets["TWILIO_AUTH_TOKEN"]
                client = Client(twilio_sid, twilio_token)
                token = client.tokens.create()
                return token.ice_servers
            except Exception:
                # Fallback to STUN. Will fail on strict corporate networks.
                return [{"urls": ["stun:stun.l.google.com:19302"]}]

        RTC_CONFIGURATION = RTCConfiguration(
            {"iceServers": get_ice_servers()}
        )

        def video_frame_callback(frame: av.VideoFrame) -> av.VideoFrame:
            img = frame.to_ndarray(format="bgr24")
            results = model.predict(img, conf=0.4, verbose=False)
            annotated = results[0].plot()
            return av.VideoFrame.from_ndarray(annotated, format="bgr24")

        webrtc_streamer(
            key="factory-monitor",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTC_CONFIGURATION,
            video_frame_callback=video_frame_callback,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True,
        )
    else:
        uploaded = st.file_uploader("Upload a floor image", type=["jpg", "jpeg", "png"])
        if uploaded is not None:
            file_bytes = uploaded.read()
            img_array = cv2.imdecode(np.frombuffer(file_bytes, dtype="uint8"), cv2.IMREAD_COLOR)
            if img_array is not None:
                results = model.predict(img_array, conf=0.4, verbose=False)
                annotated = results[0].plot()
                annotated = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                st.image(annotated, caption="Uploaded image with detections", use_container_width=True)

st.divider()

# 4. --- LIVE MACHINE DATA & ALERTS (REAL MQTT) ---
st.subheader("📈 Live Machine Data Feed")
st.caption("Topic: factory/machine_a/temp (HiveMQ public broker via WebSockets)")

# THREAD-SAFE DATA BUFFER: Streamlit state cannot be updated from background threads safely.
@st.cache_resource
def get_data_buffer():
    return deque(maxlen=20)

data_buffer = get_data_buffer()

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        client.subscribe("factory/machine_a/temp")

def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8")
    try:
        temp_value = float(payload)
        data_buffer.append(temp_value)
    except ValueError:
        pass

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
    mqtt_connected = True
except Exception as e:
    mqtt_connected = False
    st.warning(f"MQTT broker connection unavailable right now: {e}")

@st.fragment(run_every=1)
def display_live_data():
    if mqtt_connected and len(data_buffer) > 0:
        latest_temp = data_buffer[-1]

        if latest_temp > 78.0:
            st.error(f"🚨 CRITICAL WARNING: Spindle Temperature Overheating at {latest_temp}°C!")
        elif latest_temp > 76.0:
            st.warning(f"⚠️ CAUTION: Temperature rising ({latest_temp}°C). Monitor closely.")
        else:
            st.success(f"✅ Machine operating normally at {latest_temp}°C.")

        df = pd.DataFrame(list(data_buffer), columns=["Machine A Temp (°C)"])
        st.line_chart(df)
    else:
        st.info("Waiting for machine data... Run machine_simulator.py locally to publish sample values.")

display_live_data()

st.divider()

# 5. --- SARVAM AI AUDIO SECTION ---
st.subheader("🎙️ Voice-Activated Maintenance Logging")
st.caption("Optional: add SARVAM_API_KEY in Streamlit secrets to enable transcription.")

sarvam_key = st.secrets.get("SARVAM_API_KEY", os.getenv("SARVAM_API_KEY", ""))
audio_value = st.audio_input("Click to record a maintenance log")

if audio_value is not None:
    if not sarvam_key:
        st.info("Transcription is disabled until SARVAM_API_KEY is configured.")
    elif st.button("Transcribe Log with Sarvam AI"):
        with st.spinner("Processing audio..."):
            url = "https://api.sarvam.ai/speech-to-text"
            headers = {"api-subscription-key": sarvam_key}
            files = {"file": ("log.wav", audio_value.getvalue(), "audio/wav")}

            try:
                response = requests.post(url, headers=headers, files=files, timeout=60)
                if response.status_code == 200:
                    transcript = response.json().get("transcript", "No transcript found.")
                    st.success("Log Transcribed Successfully!")
                    st.text_area("Digital Log Entry:", value=transcript, height=100)
                else:
                    st.error(f"API Error: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"Failed to connect to Sarvam AI: {e}")