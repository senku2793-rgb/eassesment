from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import os
import json
from werkzeug.utils import secure_filename
from PIL import Image, ImageStat
from datetime import datetime

UPLOAD_FOLDER = 'uploads'
DATA_FILE = 'data.json'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'dev-secret-change-me'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_data():
    if not os.path.exists(DATA_FILE):
        data = {'answer_key': {'total_questions': 10}, 'submissions': []}
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f)
        return data
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def simulate_score(image_path, total_questions):
    try:
        img = Image.open(image_path).convert('L')
        stat = ImageStat.Stat(img)
        avg = stat.mean[0]  # 0-255 brightness
        # Assume darker image = more filled bubbles. Map to score.
        filled_ratio = max(0.0, min(1.0, (255.0 - avg) / 255.0))
        score = int(round(filled_ratio * total_questions))
        return score
    except Exception:
        return 0

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        role = request.form.get('role')
        if not username or role not in ('student', 'teacher'):
            flash('Provide a name and select a role')
            return redirect(url_for('login'))
        session['username'] = username
        session['role'] = role
        if role == 'student':
            return redirect(url_for('student'))
        return redirect(url_for('teacher'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/student')
def student():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    data = load_data()
    username = session.get('username')
    subs = [s for s in data.get('submissions', []) if s.get('username') == username]
    return render_template('student.html', submissions=subs, answer_key=data.get('answer_key', {}))

@app.route('/upload', methods=['POST'])
def upload():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    if 'image' not in request.files:
        flash('No file part')
        return redirect(url_for('student'))
    file = request.files['image']
    if file.filename == '' or not allowed_file(file.filename):
        flash('Invalid file')
        return redirect(url_for('student'))
    filename = secure_filename(f"{session.get('username')}_{int(datetime.utcnow().timestamp())}_{file.filename}")
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)
    data = load_data()
    total = data.get('answer_key', {}).get('total_questions', 10)
    score = simulate_score(path, total)
    submission = {
        'username': session.get('username'),
        'filename': filename,
        'score': score,
        'total': total,
        'timestamp': datetime.utcnow().isoformat()
    }
    data.setdefault('submissions', []).append(submission)
    save_data(data)
    return render_template('upload_result.html', submission=submission)

@app.route('/teacher', methods=['GET'])
def teacher():
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))
    data = load_data()
    subs = list(reversed(data.get('submissions', [])))
    return render_template('teacher.html', submissions=subs, answer_key=data.get('answer_key', {}))

@app.route('/set_key', methods=['POST'])
def set_key():
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))
    try:
        total = int(request.form.get('total_questions', 10))
    except ValueError:
        total = 10
    data = load_data()
    data['answer_key'] = {'total_questions': total}
    save_data(data)
    flash('Answer key updated')
    return redirect(url_for('teacher'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
