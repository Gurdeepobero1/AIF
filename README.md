# factory_ai_center

# 🏭 Automated AI-Powered Factory Command Center

## 📌 Overview
The Automated Shop-Floor Command Center is a real-time, multi-modal dashboard designed to eliminate data silos in modern manufacturing environments. This system acts as a lightweight SCADA (Supervisory Control and Data Acquisition) interface, integrating physical machine data, AI-driven visual monitoring, and voice-activated maintenance logging into a single, centralized platform.

Built with a focus on modern Industrial and Production engineering principles, this project demonstrates how to effectively track OEE (Overall Equipment Effectiveness), reduce reactive maintenance, and digitize shop-floor workflows.

## ✨ Key Features
* **Industrial IoT Integration (MQTT):** Subscribes to real-time machine telemetry (e.g., spindle temperatures) using a publish/subscribe architecture, simulating live CNC and conveyor line data.
* **Automated Safety Logic:** Actively monitors data streams against defined safety thresholds, triggering real-time UI alerts if equipment enters a critical state.
* **Computer Vision Monitoring (YOLOv8):** Integrates live RTSP/webcam feeds with lightweight, real-time object detection to monitor the factory floor for parts, personnel, and potential hazards.
* **Voice-Activated Maintenance Logging (Sarvam AI):** Utilizes an advanced speech-to-text API (optimized for Indian languages and regional contexts) to allow operators to log maintenance issues hands-free.

## 🛠️ Tech Stack
* **Frontend/UI:** Python, Streamlit, Pandas
* **IoT/Networking:** Paho-MQTT, HiveMQ (Public Broker)
* **Computer Vision:** OpenCV, Ultralytics (YOLOv8n)
* **Artificial Intelligence:** Sarvam AI (Speech-to-Text API)

## 🚀 How to Run Locally

**1. Clone the repository**
```bash
git clone [https://github.com/YOUR_USERNAME/factory-ai-command-center.git](https://github.com/YOUR_USERNAME/factory-ai-command-center.git)
cd factory-ai-command-center