# factory_ai_center

# 🏭 Automated AI-Powered Factory Command Center

## 📌 Overview
The Automated Shop-Floor Command Center is a real-time, multi-modal dashboard designed to reduce data silos in manufacturing environments. It combines machine telemetry, AI-driven visual monitoring, and voice-activated maintenance logging in one Streamlit app.

## ✨ Key Features
- **Industrial IoT Integration (MQTT):** Subscribes to real-time machine telemetry using HiveMQ public broker.
- **Automated Safety Logic:** Generates warnings and critical alerts when temperature crosses thresholds.
- **Computer Vision Monitoring (YOLOv8):** Runs object detection on webcam frame (local) or uploaded images (cloud-friendly).
- **Voice-Activated Maintenance Logging (Sarvam AI):** Optional speech-to-text using API key from environment/secrets.

## 🛠️ Tech Stack
- **Frontend/UI:** Python, Streamlit, Pandas
- **IoT/Networking:** Paho-MQTT, HiveMQ (Public Broker)
- **Computer Vision:** OpenCV, Ultralytics (YOLOv8n)
- **Speech-to-Text:** Sarvam AI

## 🚀 Run Locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

In a second terminal, you can publish demo MQTT values:
```bash
python machine_simulator.py
```

## ☁️ Deploy to Streamlit Community Cloud
1. Push this repo to GitHub.
2. In Streamlit Community Cloud, create an app with:
   - **Main file path:** `app.py`
   - **Python requirements:** `requirements.txt`
   - **System packages:** `packages.txt`
3. (Optional) Add Sarvam API key in **App settings → Secrets**:

```toml
SARVAM_API_KEY = "your_key_here"
```

4. Deploy and open the app URL.

### Notes for cloud deployment
- Cloud environments usually cannot access your local webcam device; use image upload mode for detection.
- MQTT depends on outbound network access to `broker.hivemq.com`.
- If model download/connectivity is temporarily unavailable, retry deployment/restart.
