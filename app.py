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
import random

# Force Ultralytics to use a writable directory immediately
os.environ["YOLO_CONFIG_DIR"] = "/tmp/Ultralytics"

# 1. --- PAGE CONFIGURATION & CUSTOM CSS ---
st.set_page_config(page_title="ACME Sentinel | Neural Operations", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* Aggressive styling for a tech-forward look */
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; }
    header {visibility: hidden;}
    
    /* Neumorphic/Cyber Metrics */
    div[data-testid="metric-container"] {
        background: linear-gradient(145deg, #1e1e1e, #252525);
        border: 1px solid #333;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        border-left: 4px solid #00f2fe;
    }
    
    /* Terminal-style AI Log */
    .ai-log-box {
        background-color: #0a0a0a;
        color: #00ff41;
        font-family: 'Courier New', Courier, monospace;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #333;
        height: 250px;
        overflow-y: hidden;
        font-size: 0.85rem;
    }
    
    hr { border-top: 1px solid rgba(255,255,255,0.1); }
    </style>
""", unsafe_allow_html=True)

cv2_available = importlib.util.find_spec("cv2") is not None

def get_cv2_module():
    if not cv2_available: return None
    return importlib.import_module("cv2")

# 2. --- SIDEBAR (CREDENTIALS & AI STATUS) ---
with st.sidebar:
    st.markdown("### 🌐 ACME Corporation")
    st.caption("SENTINEL NEURAL ENGINE v4.0")
    st.divider()
    
    st.subheader("Operator Sync")
    st.markdown("**ID:** ACME-OP-77")
    st.markdown("**Clearance:** OMEGA")
    
    st.divider()
    st.subheader("Core Systems")
    st.markdown("🧠 **Sentinel AI:** ACTIVE")
    st.markdown("📡 **Telemetry Grid:** SYNCED")
    st.markdown("👁️ **Spatial Vision:** ONLINE")

# 3. --- MAIN DASHBOARD HEADER ---
st.title("ACME Global Operations Node")
st.markdown("Continuous AI inference and spatial monitoring active.")

# 4. --- TOP-LEVEL KPI METRICS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Spindle Core Temp", "72.4°C", "Stable")
col2.metric("Yield Rate", "1,240 U/hr", "+2.4%")
col3.metric("System Entropy", "12.4%", "-0.5%")
col4.metric("Anomaly Detections", "0", "Clear")

st.divider()

# 5. --- CORE DASHBOARD GRID ---
vision_col, telemetry_col, ai_col = st.columns([2.5, 2, 1.5], gap="large")

# VISION LAYER
with vision_col:
    st.subheader("👁️ Sentinel Vision Stream")
    st.caption("Real-time YOLOv8 spatial awareness.")
    
    @st.cache_resource
    def load_model():
        return YOLO("yolov8n.pt")

    try:
        model = load_model()
        model_ready = True
    except Exception as e:
        model = None
        model_ready = False
        st.error(f"Vision Core Offline: {e}")

    if model_ready:
        input_mode = st.radio("Vision Source", ["Live Neural Stream", "Static Data Ingestion"], horizontal=True, label_visibility="collapsed")

        if input_mode == "Live Neural Stream":
            @st.cache_data
            def get_ice_servers():
                try:
                    from twilio.rest import Client
                    twilio_sid = st.secrets["TWILIO_ACCOUNT_SID"]
                    twilio_token = st.secrets["TWILIO_AUTH_TOKEN"]
                    client = Client(twilio_sid, twilio_token)
                    return client.tokens.create().ice_servers
                except Exception:
                    return [{"urls": ["stun:stun.l.google.com:19302"]}]

            RTC_CONFIGURATION = RTCConfiguration({"iceServers": get_ice_servers()})

            def video_frame_callback(frame: av.VideoFrame) -> av.VideoFrame:
                img = frame.to_ndarray(format="bgr24")
                results = model.predict(img, conf=0.4, verbose=False)
                annotated = results[0].plot()
                return av.VideoFrame.from_ndarray(annotated, format="bgr24")

            webrtc_streamer(
                key="acme-vision",
                mode=WebRtcMode.SENDRECV,
                rtc_configuration=RTC_CONFIGURATION,
                video_frame_callback=video_frame_callback,
                media_stream_constraints={"video": True, "audio": False},
                async_processing=True,
            )
        else:
            uploaded = st.file_uploader("Upload Frame Data", type=["jpg", "jpeg", "png"])
            if uploaded is not None:
                file_bytes = uploaded.read()
                img_array = cv2.imdecode(np.frombuffer(file_bytes, dtype="uint8"), cv2.IMREAD_COLOR)
                if img_array is not None:
                    results = model.predict(img_array, conf=0.4, verbose=False)
                    annotated = results[0].plot()
                    st.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB), use_container_width=True)

# TELEMETRY LAYER
with telemetry_col:
    st.subheader("📈 Live Telemetry Matrix")
    st.caption("CNC Unit Alpha - Spindle Core (°C)")

    @st.cache_resource
    def get_data_buffer():
        return deque(maxlen=40)

    data_buffer = get_data_buffer()

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0: client.subscribe("factory/machine_a/temp")

    def on_message(client, userdata, msg):
        try:
            data_buffer.append(float(msg.payload.decode("utf-8")))
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
    except Exception:
        mqtt_connected = False

    @st.fragment(run_every=1)
    def display_live_data():
        if mqtt_connected and len(data_buffer) > 0:
            df = pd.DataFrame(list(data_buffer), columns=["Temp (°C)"])
            st.area_chart(df, height=250, use_container_width=True, color="#00f2fe")
        else:
            st.info("Awaiting telemetry sync... Start edge simulator.")

    display_live_data()

# AI PREDICTIVE LAYER
with ai_col:
    st.subheader("🧠 Neural Engine")
    st.caption("Predictive Heuristics Stream")
    
    @st.fragment(run_every=2)
    def ai_inference_log():
        if len(data_buffer) > 0:
            latest = data_buffer[-1]
            log_entries = []
            
            # Simulate active AI reasoning based on live data
            log_entries.append(f"> INGEST: Temp {latest:.2f}°C")
            if latest > 78.0:
                log_entries.append("> ALERT: Thermal runaway detected. Intervention recommended.")
                log_entries.append("> PREDICTION: Failure in 4.2 mins.")
            elif latest > 76.0:
                log_entries.append("> WARN: Deviation from baseline.")
                log_entries.append("> ACTION: Adjusting coolant flow +12%.")
            else:
                log_entries.append("> STATUS: Sub-system nominal.")
                log_entries.append(f"> EFFICIENCY: {random.uniform(92.0, 99.9):.1f}% optimal.")
            
            log_entries.append("> NET: Secure.")
            log_entries.append("> CYCLE: " + str(time.time())[-6:])
            
            # Render terminal UI
            log_text = "<br>".join(log_entries)
            st.markdown(f'<div class="ai-log-box">{log_text}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="ai-log-box">> WAITING FOR DATA STREAM...</div>', unsafe_allow_html=True)

    ai_inference_log()

st.divider()

# 6. --- UTILITY ACTIONS ---
with st.expander("🎙️ ACME Neural Scribe (Voice Dictation)"):
    st.caption("Securely dictate engineering logs via Sarvam AI API.")
    sarvam_key = st.secrets.get("SARVAM_API_KEY", os.getenv("SARVAM_API_KEY", ""))
    
    audio_col, text_col = st.columns([1, 2])
    with audio_col:
        audio_value = st.audio_input("Record Log Entry")
    with text_col:
        if audio_value is not None:
            if not sarvam_key:
                st.warning("Transcription blocked: Missing API Authorization.")
            elif st.button("Process Audio Log"):
                with st.spinner("Decoding audio vector..."):
                    try:
                        response = requests.post(
                            "https://api.sarvam.ai/speech-to-text", 
                            headers={"api-subscription-key": sarvam_key}, 
                            files={"file": ("log.wav", audio_value.getvalue(), "audio/wav")}, 
                            timeout=60
                        )
                        if response.status_code == 200:
                            st.success("Transcription complete.")
                            st.text_area("Parsed Output:", value=response.json().get("transcript", ""), height=100)
                        else:
                            st.error(f"API Error {response.status_code}: {response.text}")
                    except Exception as e:
                        st.error(f"Network failure reaching Sarvam nodes: {e}")