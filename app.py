import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.utils import secure_filename
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    print("WARNING: OpenCV not found. Using fallback image matching.")
import numpy as np
import math
from collections import Counter

app = Flask(__name__)
app.secret_key = 'campus_ai_secret_key'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS Users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT DEFAULT 'STUDENT')''')
    
    # Migration: Add role column if it doesn't exist
    try:
        cursor.execute('ALTER TABLE Users ADD COLUMN role TEXT DEFAULT "STUDENT"')
    except sqlite3.OperationalError:
        pass # Column already exists
    cursor.execute('''CREATE TABLE IF NOT EXISTS Reports (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, type TEXT NOT NULL, item_name TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL, location TEXT NOT NULL, date_item TEXT NOT NULL, image_path TEXT NOT NULL, status TEXT DEFAULT 'PENDING', created_at DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES Users(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS MatchResults (id INTEGER PRIMARY KEY AUTOINCREMENT, lost_report_id INTEGER NOT NULL, found_report_id INTEGER NOT NULL, score REAL NOT NULL, FOREIGN KEY (lost_report_id) REFERENCES Reports(id), FOREIGN KEY (found_report_id) REFERENCES Reports(id))''')
    
    # Insert initial hardcoded users
    users = [
        ('BIT2025077', '12122007', 'STUDENT'),
        ('BIT2025075', '25042008', 'STUDENT'),
        ('MCET', 'MCET12345', 'ADMIN')
    ]
    for username, password, role in users:
        try:
            cursor.execute('INSERT INTO Users (username, password, role) VALUES (?, ?, ?)', (username, password, role))
        except sqlite3.IntegrityError:
            pass 
    conn.commit()
    conn.close()

# Run initialization
if not os.path.exists('database.db'):
    init_db()

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- AI Matching Logic ---

def calculate_text_similarity(text1, text2):
    if not text1 or not text2:
        return 0.0
    
    # Simple manual TF-IDF / Cosine Similarity
    def get_tokens(text):
        return text.lower().split()

    t1 = get_tokens(text1)
    t2 = get_tokens(text2)
    
    vocab = set(t1 + t2)
    if not vocab: return 0.0
    
    v1 = Counter(t1)
    v2 = Counter(t2)
    
    dot = sum(v1[w] * v2[w] for w in vocab)
    norm1 = math.sqrt(sum(v1[w]**2 for w in v1))
    norm2 = math.sqrt(sum(v2[w]**2 for w in v2))
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
        
    return dot / (norm1 * norm2)

def calculate_image_similarity(img_path1, img_path2):
    if not OPENCV_AVAILABLE:
        # Fallback: simple text-based score if image matching is unavailable
        return 0.5 
        
    try:
        img1 = cv2.imread(img_path1)
        img2 = cv2.imread(img_path2)
        
        if img1 is None or img2 is None:
            return 0.0
            
        # Resize to same size for simple comparison
        img1 = cv2.resize(img1, (300, 300))
        img2 = cv2.resize(img2, (300, 300))
        
        # Convert to grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        # Simple Histogram comparison
        hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
        
        cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
        cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)
        
        similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        return max(0.0, similarity)
    except Exception as e:
        print(f"Error comparing images: {e}")
        return 0.0

def run_ai_matching(found_report_id):
    conn = get_db_connection()
    found_item = conn.execute('SELECT * FROM Reports WHERE id = ?', (found_report_id,)).fetchone()
    
    if not found_item or found_item['type'] != 'FOUND':
        conn.close()
        return

    lost_items = conn.execute('SELECT * FROM Reports WHERE type = "LOST" AND status = "PENDING"').fetchall()
    
    for lost_item in lost_items:
        # Text similarity on description + item_name
        text_sim = calculate_text_similarity(
            f"{found_item['item_name']} {found_item['description']}",
            f"{lost_item['item_name']} {lost_item['description']}"
        )
        
        # Image similarity
        img_sim = calculate_image_similarity(
            os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], found_item['image_path']),
            os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], lost_item['image_path'])
        )
        
        final_score = (img_sim * 0.7) + (text_sim * 0.3)
        
        if final_score >= 0.6: # Threshold
            # Update statuses
            conn.execute('UPDATE Reports SET status = "MATCH FOUND" WHERE id = ?', (found_item['id'],))
            conn.execute('UPDATE Reports SET status = "MATCH FOUND" WHERE id = ?', (lost_item['id'],))
            
            # Record result
            conn.execute('INSERT INTO MatchResults (lost_report_id, found_report_id, score) VALUES (?, ?, ?)',
                         (lost_item['id'], found_item['id'], final_score))
            
            conn.commit()
            break # Stop after first good match for simplicity, or continue for all
            
    conn.close()

# --- Routes ---

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('chatbot'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM Users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            if user['role'] == 'ADMIN':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('chatbot'))
        else:
            flash('Invalid Credentials!', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/chatbot')
def chatbot():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get('role') == 'ADMIN':
        return redirect(url_for('admin_dashboard'))
    return render_template('chatbot.html')

@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'ADMIN':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    # Fetch all reports for the admin
    reports = conn.execute('''
        SELECT r.*, u.username as reporter 
        FROM Reports r 
        JOIN Users u ON r.user_id = u.id 
        ORDER BY r.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('admin.html', reports=reports)

@app.route('/report', methods=['POST'])
def report_item():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    data = request.form
    image = request.files.get('image')
    
    if not image:
        return jsonify({'status': 'error', 'message': 'Image is mandatory!'}), 400

    filename = secure_filename(image.filename)
    import time
    filename = f"{int(time.time())}_{filename}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    image.save(save_path)
    
    # Store just the filename relative to uploads or the URL-friendly path
    db_image_path = filename 
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Reports (user_id, type, item_name, category, description, location, date_item, image_path, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        session['user_id'],
        data['type'].upper(),
        data['item_name'],
        data['category'],
        data['description'],
        data['location'],
        data['date_lost'],
        db_image_path,
        'PENDING'
    ))
    report_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    if data['type'].upper() == 'FOUND':
        run_ai_matching(report_id)
        
    return jsonify({'status': 'success', 'message': 'Report saved successfully!'})

@app.route('/my_reports')
def my_reports():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    reports = conn.execute('SELECT * FROM Reports WHERE user_id = ? ORDER BY created_at DESC', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('my_reports.html', reports=reports)

if __name__ == '__main__':
    import os
    # Railway/Render provide a PORT environment variable
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)
