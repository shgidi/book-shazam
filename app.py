from flask import Flask, render_template, request, jsonify, send_from_directory
from flask import Flask, render_template, request, jsonify, send_from_directory
import cv2
import numpy as np
import torch
import base64
from google.cloud import vision
import io
import os
from anthropic import Anthropic
import re

app = Flask(__name__, static_folder='static')

# Set up Google Cloud Vision client
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/shgidi/Downloads/compute-5-6-18-2835fab6d675.json'
vision_client = vision.ImageAnnotatorClient()

# Set up Anthropic client
<<<<<<< HEAD
anthropic = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
=======
anthropic = anthropic = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
>>>>>>> 9489362 (python version update)

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

@app.route('/refine_book_title', methods=['POST'])
def refine_book_title():
    data = request.json
    ocr_text = data['ocr_text']

    prompt = f"""Given the following text extracted from an image of a book cover using OCR:

{ocr_text}

Please identify and return the most likely full title of the book. If you can't determine a specific book title, return your best guess at what the title might be based on the given text. Your response should only include the book title, nothing else.
"""

    response = anthropic.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=100,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    refined_title = response.content[0].text.strip()

    return jsonify({
        'refined_title': refined_title
    })

@app.route('/rate_book', methods=['POST'])
def rate_book():
    data = request.json
    book_title = data['book_title']
    liked_books = data['liked_books']

    prompt = f"""Given the following information:

Book to rate: {book_title}

Books the user liked:
{', '.join(liked_books)}

Please provide an estimated rating out of 5 stars for the book to rate, based on the user's preferences as indicated by the books they liked. Explain your reasoning briefly.

Your response should be in the format:
Rating: [X] out of 5 stars
Reasoning: [Your explanation]
"""

    response = anthropic.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=150,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    # Extract the rating and reasoning from the response
    ai_response = response.content[0].text
    rating_match = re.search(r'Rating:\s*(\d+(?:\.\d+)?)\s*out of 5 stars', ai_response)
    reasoning_match = re.search(r'Reasoning:\s*(.+)', ai_response, re.DOTALL)

    if rating_match and reasoning_match:
        rating = float(rating_match.group(1))
        reasoning = reasoning_match.group(1).strip()
    else:
        rating = None
        reasoning = "Unable to parse rating. Full response: " + ai_response

    return jsonify({
        'rating': rating,
        'reasoning': reasoning
    })

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')