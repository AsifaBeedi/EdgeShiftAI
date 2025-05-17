import tensorflow as tf
import numpy as np
from PIL import Image
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "..", "model", "model_files", "mobilenet_v1_1.0_224_quant.tflite")
LABELS_PATH = os.path.join(BASE_DIR, "..", "model", "model_files", "labels.txt")

class ModelInterface:
    def __init__(self):
        with open(LABELS_PATH, "r") as f:
            self.labels = [line.strip() for line in f.readlines()]
        self.interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
        self.interpreter.allocate_tensors()
        self.input_index = self.interpreter.get_input_details()[0]['index']
        self.output_index = self.interpreter.get_output_details()[0]['index']

    def preprocess_image(self, image_path):
        image = Image.open(image_path).convert("RGB")
        image = image.resize((224, 224))
        img_np = np.array(image)
        if img_np.ndim == 2:
            img_np = np.stack([img_np] * 3, axis=-1)
        img_np = img_np.astype(np.uint8)
        return np.expand_dims(img_np, axis=0)

    def process_image_partition(self, image_path, partition_index=0, total_partitions=1):
        input_data = self.preprocess_image(image_path)
        self.interpreter.set_tensor(self.input_index, input_data)
        self.interpreter.invoke()
        output = self.interpreter.get_tensor(self.output_index)
        predicted_class = int(np.argmax(output))
        predicted_label = self.labels[predicted_class] if predicted_class < len(self.labels) else "Unknown"
        confidence = float(np.max(output))
        return {
            'partition': partition_index,
            'processing_time': 0,  # You can time this if you want
            'detections': [
                {
                    'class': predicted_label,
                    'confidence': confidence,
                    'location': f"Part {partition_index}/{total_partitions}"
                }
            ]
        }

    def combine_results(self, partition_results):
        # For classification, just pick the highest confidence result
        all_detections = []
        for part_result in partition_results:
            if 'detections' in part_result:
                all_detections.extend(part_result['detections'])
        if all_detections:
            best = max(all_detections, key=lambda d: d['confidence'])
            return {
                'best_class': best['class'],
                'confidence': best['confidence'],
                'all_detections': all_detections
            }
        else:
            return {'error': 'No detections'}
