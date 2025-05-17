import gradio as gr
import tensorflow as tf
import numpy as np
from PIL import Image

MODEL_PATH = r"C:\Users\Aayushi\Downloads\mobilenet_v1_1.0_224_quant (4).tflite"
LABELS_PATH = r"C:\Users\Aayushi\OneDrive\Documents\index.txt"

with open(LABELS_PATH, "r") as f:
    labels = [line.strip() for line in f.readlines()]

interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()

input_index = interpreter.get_input_details()[0]['index']
output_index = interpreter.get_output_details()[0]['index']

def preprocess_image(image):
    image = image.resize((224, 224))
    img_np = np.array(image)
    if img_np.ndim == 2:
        img_np = np.stack([img_np] * 3, axis=-1)
    img_np = img_np.astype(np.uint8)
    return np.expand_dims(img_np, axis=0)

def predict_and_show(image):
    input_data = preprocess_image(image)
    interpreter.set_tensor(input_index, input_data)
    interpreter.invoke()
    output = interpreter.get_tensor(output_index)
    predicted_class = np.argmax(output)
    predicted_label = labels[predicted_class] if predicted_class < len(labels) else "Unknown"
    return image, f"Predicted class index: {predicted_class} - Label: {predicted_label}"

iface = gr.Interface(
    fn=predict_and_show,
    inputs=gr.Image(type="pil", label="Upload an Image"),
    outputs=[gr.Image(type="pil", label="Uploaded Image"), gr.Textbox(label="Prediction Result")],
    title="MobileNet v1 TFLite Image Classifier",
    description="Upload an image, and get the predicted class index and label."
)

if __name__ == "__main__":
    iface.launch()
