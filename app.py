import os
import time
import cv2
import pandas as pd
import numpy as np
import requests
import streamlit as st
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
st.subheader("📹 Floor Monitoring (AI Enabled)")
st.caption("Run object detection on a webcam frame (local) or uploaded image (cloud).")


@st.cache_resource
def load_model():
    # Uses local file if present; otherwise lets Ultralytics fetch the official small model.
    model_source = "yolov8n.pt" if os.path.exists("yolov8n.pt") else "yolov8n.pt"
    return YOLO(model_source)


try:
    model = load_model()
    model_ready = True
except Exception as e:
    model = None
    model_ready = False
    st.error(f"Could not load YOLO model: {e}")

if model_ready:
    use_webcam = st.checkbox("Use local webcam (works in local desktop run)", value=False)

    if use_webcam:
        camera = cv2.VideoCapture(0)
        ok, frame = camera.read()
        camera.release()

        if not ok:
            st.warning("Webcam frame unavailable. On Streamlit Cloud, use image upload mode instead.")
        else:
            results = model.predict(frame, conf=0.4, verbose=False)
            annotated = results[0].plot()
            annotated = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            st.image(annotated, caption="Webcam frame with detections", use_container_width=True)
    else:
        uploaded = st.file_uploader("Upload a floor image", type=["jpg", "jpeg", "png"])
        if uploaded is not None:
            file_bytes = uploaded.read()
            img_array = cv2.imdecode(
                np.frombuffer(file_bytes, dtype="uint8"), cv2.IMREAD_COLOR  # type: ignore[attr-defined]
            )
            if img_array is None:
                st.error("Could not decode uploaded image.")
            else:
                results = model.predict(img_array, conf=0.4, verbose=False)
                annotated = results[0].plot()
                annotated = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                st.image(annotated, caption="Uploaded image with detections", use_container_width=True)
        else:
            st.info("Upload an image to run detection.")

st.divider()

# 4. --- LIVE MACHINE DATA & ALERTS (REAL MQTT) ---
st.subheader("📈 Live Machine Data Feed")
st.caption("Topic: factory/machine_a/temp (HiveMQ public broker)")

if "machine_data" not in st.session_state:
    st.session_state["machine_data"] = []


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe("factory/machine_a/temp")


def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8")
    try:
        temp_value = float(payload)
        st.session_state["machine_data"].append(temp_value)
        if len(st.session_state["machine_data"]) > 20:
            st.session_state["machine_data"].pop(0)
    except ValueError:
        pass


@st.cache_resource
def get_mqtt_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("broker.hivemq.com", 1883, 60)
    client.loop_start()
    return client


try:
    get_mqtt_client()
    mqtt_connected = True
except Exception as e:
    mqtt_connected = False
    st.warning(f"MQTT broker connection unavailable right now: {e}")

if mqtt_connected and len(st.session_state["machine_data"]) > 0:
    latest_temp = st.session_state["machine_data"][-1]

    if latest_temp > 78.0:
        st.error(f"🚨 CRITICAL WARNING: Spindle Temperature Overheating at {latest_temp}°C!")
    elif latest_temp > 76.0:
        st.warning(f"⚠️ CAUTION: Temperature rising ({latest_temp}°C). Monitor closely.")
    else:
        st.success(f"✅ Machine operating normally at {latest_temp}°C.")

    df = pd.DataFrame(st.session_state["machine_data"], columns=["Machine A Temp (°C)"])
    st.line_chart(df)
else:
    st.info("Waiting for machine data... Run machine_simulator.py locally to publish sample values.")

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

# 6. --- AUTO REFRESH LOOP ---
time.sleep(1)
st.rerun()
