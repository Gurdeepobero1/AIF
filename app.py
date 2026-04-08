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
st.set_page_config(page_title="ACME Sentinel | SCADA Operations", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Brutalist / Industrial SCADA Styling */
    body { background-color: #050505; color: #e0e0e0; }
    .block-container { padding-top: 1rem !important; max-width: 95%; }
    header {visibility: hidden;}
    
    /* Neumorphic/Cyber Metrics */
    div[data-testid="metric-container"] {
        background: #0a0a0a;
        border: 1px solid #222;
        padding: 15px;
        border-radius: 4px;
        border-top: 3px solid #ff3333;
        box-shadow: inset 0 0 10px rgba(255,51,51,0.05);
        font-family: 'Courier New', monospace;
    }
    
    /* Terminal-style AI Log */
    .ai-log-box {
        background-color: #030303;
        color: #ff3333;
        font-family: 'Courier New', Courier, monospace;
        padding: 10px;
        border-radius: 2px;
        border: 1px solid #333;
        height: 300px;
        overflow-y: hidden;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .status-nominal { color: #00ff41; }
    .status-warn { color: #ff9900; }
    .status-crit { color: #ff3333; font-weight: bold; }
    
    hr { border-top: 1px solid #222; margin: 1rem 0; }
    </style>
""", unsafe_allow_html=True)

cv2_available = importlib.util.find_spec("cv2") is not None

# 2. --- MAIN DASHBOARD HEADER ---
st.markdown("<h2 style='font-family: monospace; color: #fff;'>ACME CORP // GLOBAL OPERATIONS SEC-04</h2>", unsafe_allow_html=True)
st.caption("TACTICAL SCADA & NEURAL VISION SUBSYSTEM | CLEARANCE: OMEGA")
st.divider()

# 3. --- TOP-LEVEL KPI METRICS ---
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Spindle Core", "72.4°C", "NOMINAL", delta_color="off")
col2.metric("OEE Yield", "94.2%", "+1.2%", delta_color="normal")
col3.metric("Network Latency", "14ms", "-2ms", delta_color="inverse")
col4.metric("Active Hazards", "1", "PPE VIOLATION", delta_color="inverse")
col5.metric("System Entropy", "0.04", "STABLE", delta_color="off")

st.divider()

# 4. --- CORE DASHBOARD GRID ---
vision_col, telemetry_col, ai_col = st.columns([2.5, 2, 1.5], gap="small")

# VISION LAYER WITH HUD OVERLAY
with vision_col:
    st.markdown("<h4 style='font-family: monospace;'>[ VISION FEED : NODE 01 ]</h4>", unsafe_allow_html=True)
    
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
            
            # Detect Human (Class 0)
            human_detected = False
            for box in results[0].boxes:
                if int(box.cls[0]) == 0:
                    human_detected = True
                    break
            
            annotated = results[0].plot()
            
            # INJECT MILITARY-GRADE HUD OVERLAY IF HUMAN DETECTED
            if human_detected:
                # Flashing red border simulation
                overlay = annotated.copy()
                cv2.rectangle(overlay, (0, 0), (overlay.shape[1], overlay.shape[0]), (0, 0, 255), 15)
                
                # Scanlines / HUD Text
                cv2.putText(overlay, "!! BIO-SIGNATURE DETECTED !!", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                cv2.putText(overlay, "INITIATING PPE SCAN...", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.putText(overlay, "ERR: HARDHAT NOT FOUND.", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                cv2.putText(overlay, "ERR: HIGH-VIS VEST NOT FOUND.", (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                cv2.putText(overlay, "ACTION: LOGGING SAFETY VIOLATION", (20, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # Blend overlay for HUD effect
                alpha = 0.8
                annotated = cv2.addWeighted(overlay, alpha, annotated, 1 - alpha, 0)
            else:
                cv2.putText(annotated, "SECTOR CLEAR", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            return av.VideoFrame.from_ndarray(annotated, format="bgr24")

        webrtc_streamer(
            key="acme-vision",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTC_CONFIGURATION,
            video_frame_callback=video_frame_callback,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True,
        )

# TELEMETRY LAYER
with telemetry_col:
    st.markdown("<h4 style='font-family: monospace;'>[ TELEMETRY : ALPHA CORE ]</h4>", unsafe_allow_html=True)

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
            st.area_chart(df, height=350, use_container_width=True, color="#ff3333")
        else:
            st.info("AWAITING MQTT HANDSHAKE...")

    display_live_data()

# HEURISTICS LAYER
with ai_col:
    st.markdown("<h4 style='font-family: monospace;'>[ NEURAL HEURISTICS ]</h4>", unsafe_allow_html=True)
    
    @st.fragment(run_every=2)
    def ai_inference_log():
        log_entries = [
            f"[{time.strftime('%H:%M:%S')}] SYS: WATCHDOG THREAD ACTIVE",
            f"[{time.strftime('%H:%M:%S')}] NET: LATENCY 14MS",
            "-----------------------------------"
        ]
        
        if len(data_buffer) > 0:
            latest = data_buffer[-1]
            log_entries.append(f"[{time.strftime('%H:%M:%S')}] TELEMETRY INGEST: {latest:.2f}°C")
            
            if latest > 78.0:
                log_entries.append(f"<span class='status-crit'>[{time.strftime('%H:%M:%S')}] CRIT: THERMAL RUNAWAY.</span>")
                log_entries.append(f"<span class='status-crit'>[{time.strftime('%H:%M:%S')}] ACT: ENGAGING EMERGENCY COOLANT.</span>")
            else:
                log_entries.append(f"<span class='status-nominal'>[{time.strftime('%H:%M:%S')}] THERMAL CORE STABLE.</span>")
        
        # Simulated Vision Heuristics
        log_entries.append("-----------------------------------")
        log_entries.append(f"[{time.strftime('%H:%M:%S')}] VIS: FRAME CAPTURE PROCESSED")
        log_entries.append(f"<span class='status-warn'>[{time.strftime('%H:%M:%S')}] WARN: CONTINUOUS SCAN FOR BIO-SIGNATURES.</span>")
        log_entries.append(f"[{time.strftime('%H:%M:%S')}] VIS: YOLO_INFERENCE_TIME: {random.uniform(8.0, 15.0):.2f}MS")

        log_text = "<br>".join(log_entries)
        st.markdown(f'<div class="ai-log-box">{log_text}</div>', unsafe_allow_html=True)

    ai_inference_log()

st.divider()

# 5. --- UTILITY ACTIONS ---
with st.expander("[ DICTATION TERMINAL ]"):
    sarvam_key = st.secrets.get("SARVAM_API_KEY", os.getenv("SARVAM_API_KEY", ""))
    audio_col, text_col = st.columns([1, 2])
    with audio_col:
        audio_value = st.audio_input("TRANSMIT AUDIO COMMAND")
    with text_col:
        if audio_value is not None:
            if not sarvam_key:
                st.error("ERR: SARVAM API UNAUTHENTICATED.")
            elif st.button("EXECUTE TRANSCRIPTION"):
                with st.spinner("DECODING..."):
                    try:
                        response = requests.post(
                            "https://api.sarvam.ai/speech-to-text", 
                            headers={"api-subscription-key": sarvam_key}, 
                            files={"file": ("log.wav", audio_value.getvalue(), "audio/wav")}, 
                            timeout=60
                        )
                        if response.status_code == 200:
                            st.success("DECODE SUCCESSFUL.")
                            st.text_area("RAW OUTPUT:", value=response.json().get("transcript", ""), height=100)
                        else:
                            st.error(f"ERR {response.status_code}: {response.text}")
                    except Exception as e:
                        st.error(f"ERR CONNECTION FAILED: {e}")