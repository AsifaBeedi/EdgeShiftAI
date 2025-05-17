# EdgeShiftAI


**EdgeShiftAI** is a lightweight, peer-to-peer AI inference system designed to perform on-device machine learning tasks without relying on cloud services. This eliminates dependency on external servers, ensuring privacy, faster response times, and offline capabilities.

## Key Features

- **Peer-to-Peer Communication:** Devices communicate directly using ZeroMQ, enabling decentralized AI processing.
- **Cloud-Independent:** No data leaves the local network, enhancing security and privacy.
- **Efficient AI Inference:** Uses TensorFlow Lite models for fast, lightweight machine learning on edge devices.
- **Simple User Interface:** Intuitive Gradio-based UI for easy interaction with the AI model.

## How It Works

- The model server runs locally and processes AI inference requests sent by client devices.
- Communication happens via ZeroMQ sockets, facilitating real-time, low-latency data exchange.
- The system supports image classification using quantized MobileNet models for efficient resource usage.

## Setup & Usage

1. Clone the repository:
   ```bash
   git clone https://github.com/AsifaBeedi/EdgeShiftAI.git
   cd EdgeShiftAI
