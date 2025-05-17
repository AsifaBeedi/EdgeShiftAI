import requests
import os

url = "https://storage.googleapis.com/download.tensorflow.org/models/tflite/mobilenet_v1_1.0_224_quant.tflite"
save_path = os.path.join("model", "model_files", "mobilenet_v1_1.0_224_quant.tflite")
os.makedirs(os.path.dirname(save_path), exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0"
}

print(f"📥 Downloading model from {url}")

response = requests.get(url, headers=headers)
if response.status_code == 200:
    with open(save_path, 'wb') as f:
        f.write(response.content)
    print(f"✅ Model saved to {save_path}")
    print(f"📦 Model file size: {os.path.getsize(save_path)} bytes")
else:
    print(f"❌ Failed to download. Status code: {response.status_code}")
