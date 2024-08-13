from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import torch
import base64
from google.cloud import vision
import io
import os

app = Flask(__name__)

# Set up Google Cloud Vision client
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/shgidi/Downloads/compute-5-6-18-2835fab6d675.json'
vision_client = vision.ImageAnnotatorClient()

# Load YOLOv5 model
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
model.classes = [73]  # 73 is the class index for 'book' in COCO dataset

def detect_books(image):
    results = model(image)
    return results.xyxy[0].cpu().numpy()

def perform_ocr(image, box):
    x1, y1, x2, y2 = map(int, box[:4])
    roi = image[y1:y2, x1:x2]
    
    # Convert the ROI to bytes
    is_success, buffer = cv2.imencode(".jpg", roi)
    io_buf = io.BytesIO(buffer)
    
    # Perform OCR using Google Cloud Vision API
    vision_image = vision.Image(content=io_buf.getvalue())
    response = vision_client.text_detection(image=vision_image)
    texts = response.text_annotations
    
    if texts:
        return texts[0].description.strip()
    return "No text detected"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        img = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_UNCHANGED)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        detections = detect_books(img_rgb)
        
        result_img = img.copy()
        book_info = []
        for det in detections:
            x1, y1, x2, y2, conf, cls = det
            cv2.rectangle(result_img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            text = perform_ocr(img, det)
            book_info.append({"bbox": det[:4].tolist(), "text": text})
        
        _, buffer = cv2.imencode('.jpg', result_img)
        img_str = base64.b64encode(buffer).decode()
        
        return jsonify({
            'image': f'data:image/jpeg;base64,{img_str}',
            'books': book_info
        })
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)