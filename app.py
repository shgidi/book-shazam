from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import cv2
import numpy as np
import torch
import base64
from google.cloud import vision
import io
import os
from anthropic import Anthropic
import re
from database_models import db, User, LikedBook
from PIL import Image
import exifread

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'random-key'  # Change this to a random secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookshazam.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Set up Google Cloud Vision client
vision_client = vision.ImageAnnotatorClient()

# Set up Anthropic client
anthropic = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

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

def fix_image_rotation(image_file):
    image = Image.open(image_file)
    
    # Check if the image has EXIF data
    exif = image._getexif()
    if exif is not None:
        # EXIF orientation tag
        orientation_key = 274
        if orientation_key in exif:
            orientation = exif[orientation_key]
            
            # Rotate the image based on EXIF orientation
            if orientation == 3:
                image = image.rotate(180, expand=True)
            elif orientation == 6:
                image = image.rotate(270, expand=True)
            elif orientation == 8:
                image = image.rotate(90, expand=True)
    
    # Convert PIL Image to numpy array for OpenCV
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
@app.route('/')
def index():
    if current_user.is_authenticated:
        liked_books = [book.title for book in current_user.liked_books]
    else:
        liked_books = []
    return render_template('index.html', liked_books=liked_books)
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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists')
            return redirect(url_for('register'))
        
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            print(username,'logged in')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/add_liked_book', methods=['POST'])
@login_required
def add_liked_book():
    data = request.json
    book_title = data['book_title']
    
    existing_book = LikedBook.query.filter_by(user_id=current_user.id, title=book_title).first()
    if not existing_book:
        new_book = LikedBook(title=book_title, user_id=current_user.id)
        db.session.add(new_book)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Book added to liked books'})
    else:
        return jsonify({'success': False, 'message': 'Book already in liked books'})

@app.route('/remove_liked_book', methods=['POST'])
@login_required
def remove_liked_book():
    data = request.json
    book_title = data['book_title']
    
    book = LikedBook.query.filter_by(user_id=current_user.id, title=book_title).first()
    if book:
        db.session.delete(book)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Book removed from liked books'})
    else:
        return jsonify({'success': False, 'message': 'Book not found in liked books'})
    data = request.json
    book_title = data['book_title']
    
    book = LikedBook.query.filter_by(user_id=current_user.id, title=book_title).first()
    if book:
        db.session.delete(book)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Book removed from liked books'})
    else:
        return jsonify({'success': False, 'message': 'Book not found in liked books'})

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
@login_required
def rate_book():
    data = request.json
    book_title = data['book_title']
    liked_books = data['liked_books']

    prompt = f"""Given the following information:

Book to rate: {book_title}

Books the user liked:
{', '.join(liked_books)}

Please provide an estimated rating out of 5 stars for the book to rate, based on the user's preferences as indicated by the books they liked. If you're not familiar with the book, make an educated guess based on the title and the user's preferences. Explain your reasoning briefly.

Your response should be in the format:
Rating: [X] out of 5 stars
Reasoning: [Your explanation]
"""

    response = anthropic.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=100,
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

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    # Check if user has at least 3 liked books
    if current_user.liked_books.count() < 3:
        return jsonify({
            'error': 'Please add at least 3 books to your liked books before uploading an image.'
        }), 400

    file = request.files['file']
    
    # Fix image rotation
    img = fix_image_rotation(file)
    
    im_id = np.random.rand()
    cv2.imwrite(f'./images/img_{im_id}.jpg',img)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    print('image uploaded')
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

def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    init_db()  # Initialize the database before running the app
    app.run(host='0.0.0.0',debug=True)
    #app.run(ssl_context=('full_chain.crt', 'private.key'),host='0.0.0.0', port=443,debug=True)
