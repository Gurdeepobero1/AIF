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

# 1. --- PAGE CONFIGURATION & CUSTOM CSS ---
st.set_page_config(page_title="Command Center | Oberoi Integrated Automation", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* Global layout adjustments */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* Clean up the header */
    header {visibility: hidden;}
    
    /* Metric styling */
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Dark mode adaptations for metrics */
    @media (prefers-color-scheme: dark) {
        div[data-testid="metric-container"] {
            background-color: #1e1e1e;
            border: 1px solid #333;
        }
    }
    
    /* Custom divider */
    hr {
        margin-top: 1.5rem;
        margin-bottom: 1.5rem;
        border: 0;
        border-top: 1px solid rgba(255,255,255,0.1);
    }
    </style>
""", unsafe_allow_html=True)

cv2_available = importlib.util.find_spec("cv2") is not None

# 2. --- SIDEBAR (CREDENTIALS & SYSTEM STATUS) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2083/2083213.png", width=60) # Placeholder logo
    st.title("Oberoi Integrated Automation")
    st.caption("Enterprise SCADA & Vision Systems")
    st.divider()
    
    st.subheader("Operator Credentials")
    st.markdown("**User:** G. Oberoi")
    st.markdown("**Role:** Lead Systems Architect")
    st.markdown("**Clearance:** Tier 1 (Admin)")
    
    st.divider()
    st.subheader("System Health")
    st.markdown("🟢 **MQTT Broker:** Connected")
    st.markdown("🟢 **Vision Model:** YOLOv8n Active")
    st.markdown("🟡 **TURN Server:** Standby (STUN Active)")
    
    st.divider()
    st.caption("BATCAM Vision Module v2.1")

# 3. --- MAIN DASHBOARD HEADER ---
st.title("🏭 Factory Floor Command Center")
st.markdown("Real-time telemetry and spatial monitoring for Sector 4.")

# 4. --- TOP-LEVEL KPI METRICS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Spindle Temperature", "72.4°C", "-0.8°C")
col2.metric("Parts Produced", "1,240", "+15/hr")
col3.metric("OEE", "88.2%", "+1.2%")
col4.metric("Active Hazards", "0", "Clear")

st.divider()

# 5. --- CORE DASHBOARD GRID ---
# Split the layout: 60% Vision, 40% Telemetry
vision_col, telemetry_col = st.columns([3, 2], gap="large")

with vision_col:
    st.subheader("📹 Spatial Monitoring Feed")
    st.caption("Live floor analysis and object detection.")
    
    @st.cache_resource
    def load_model():
        return YOLO("yolov8n.pt")

    try:
        model = load_model()
        model_ready = True
    except Exception as e:
        model = None
        model_ready = False
        st.error(f"System Error: YOLO model failed to initialize. {e}")

    if model_ready:
        input_mode = st.radio("Stream Source", ["Live Edge Feed (WebRTC)", "Static Inspection Upload"], horizontal=True, label_visibility="collapsed")

        if input_mode == "Live Edge Feed (WebRTC)":
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
                    return [{"urls": ["stun:stun.l.google.com:19302"]}]

            RTC_CONFIGURATION = RTCConfiguration({"iceServers": get_ice_servers()})

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
            uploaded = st.file_uploader("Upload Inspection Image", type=["jpg", "jpeg", "png"])
            if uploaded is not None:
                file_bytes = uploaded.read()
                img_array = cv2.imdecode(np.frombuffer(file_bytes, dtype="uint8"), cv2.IMREAD_COLOR)
                if img_array is not None:
                    results = model.predict(img_array, conf=0.4, verbose=False)
                    annotated = results[0].plot()
                    annotated = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                    st.image(annotated, use_container_width=True)

with telemetry_col:
    st.subheader("📈 Live Telemetry")
    st.caption("CNC Unit Alpha - Spindle Core (°C)")

    @st.cache_resource
    def get_data_buffer():
        return deque(maxlen=30)

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
        st.error("Network Partition: Cannot reach telemetry broker.")

    @st.fragment(run_every=1)
    def display_live_data():
        if mqtt_connected and len(data_buffer) > 0:
            latest_temp = data_buffer[-1]

            if latest_temp > 78.0:
                st.error(f"🚨 CRITICAL OVERTEMP: {latest_temp}°C")
            elif latest_temp > 76.0:
                st.warning(f"⚠️ TEMP RISING: {latest_temp}°C")
            else:
                st.success(f"✅ NOMINAL: {latest_temp}°C")

            df = pd.DataFrame(list(data_buffer), columns=["Temp (°C)"])
            st.area_chart(df, height=250, use_container_width=True) # Upgraded to area chart for better modern look
        else:
            st.info("Awaiting telemetry sync... Start edge simulator.")

    display_live_data()

st.divider()

# 6. --- UTILITY ACTIONS ---
with st.expander("🛠️ Maintenance Logs & Voice Dictation"):
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
                    url = "https://api.sarvam.ai/speech-to-text"
                    headers = {"api-subscription-key": sarvam_key}
                    files = {"file": ("log.wav", audio_value.getvalue(), "audio/wav")}

                    try:
                        response = requests.post(url, headers=headers, files=files, timeout=60)
                        if response.status_code == 200:
                            transcript = response.json().get("transcript", "No text detected.")
                            st.success("Transcription complete.")
                            st.text_area("Logged Output:", value=transcript, height=100)
                        else:
                            st.error(f"API Error {response.status_code}: {response.text}")
                    except Exception as e:
                        st.error(f"Network failure reaching Sarvam nodes: {e}")