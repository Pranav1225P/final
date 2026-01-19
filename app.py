import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.secret_key = 'campus_ai_secret_key'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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
    try:
        vectorizer = TfidfVectorizer().fit_transform([text1, text2])
        vectors = vectorizer.toarray()
        return cosine_similarity(vectors)[0][1]
    except:
        return 0.0

def calculate_image_similarity(img_path1, img_path2):
    try:
        img1 = cv2.imread(img_path1)
        img2 = cv2.imread(img_path2)
        
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
    return render_template('chatbot.html')

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
