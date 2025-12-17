from flask import Flask, render_template, request, redirect, url_for, session, flash
import os, json, smtplib
from werkzeug.utils import secure_filename
from PIL import Image, ImageStat
from datetime import datetime
from email.mime.text import MIMEText

# =======================
# Configuration
# =======================
UPLOAD_FOLDER = 'uploads'
DATA_FILE = 'data.json'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

EMAIL_ADDRESS = "yourgmail@gmail.com"
EMAIL_PASSWORD = "YOUR_GMAIL_APP_PASSWORD"

app = Flask(__name__)
app.secret_key = 'dev-secret'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =======================
# OOP Classes
# =======================
class User:
    def __init__(self, username, role, email=None):
        self.username = username
        self.role = role
        self.email = email

    def is_student(self):
        return self.role == 'student'

    def is_teacher(self):
        return self.role == 'teacher'

class Submission:
    def __init__(self, username, filename, score, total):
        self.username = username
        self.filename = filename
        self.score = score
        self.total = total
        self.timestamp = datetime.utcnow().isoformat()

# =======================
# Utility Functions
# =======================
def load_data():
    if not os.path.exists(DATA_FILE):
        data = {"answer_key": {"total_questions": 10}, "submissions": []}
        save_data(data)
        return data
    with open(DATA_FILE) as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_score(image_path, total):
    img = Image.open(image_path).convert('L')
    avg = ImageStat.Stat(img).mean[0]
    ratio = max(0, min(1, (255 - avg) / 255))
    return int(round(ratio * total))

def send_email(to_email, subject, message):
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()

# =======================
# Routes (Controller)
# =======================
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = User(
            request.form['username'],
            request.form['role'],
            request.form.get('email')
        )
        session['username'] = user.username
        session['role'] = user.role
        session['email'] = user.email
        return redirect(url_for(user.role))
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
    subs = [s for s in data['submissions'] if s['username'] == session['username']]
    return render_template('student.html', submissions=subs)

@app.route('/upload', methods=['POST'])
def upload():
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    file = request.files['image']
    if not file or not allowed_file(file.filename):
        flash("Invalid file")
        return redirect(url_for('student'))

    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    data = load_data()
    total = data['answer_key']['total_questions']
    score = calculate_score(path, total)

    submission = Submission(session['username'], filename, score, total)
    data['submissions'].append(submission.__dict__)
    save_data(data)

    send_email(
        session.get('email'),
        "E-Assessment Result",
        f"Hello {submission.username}, your score is {score}/{total}."
    )

    return render_template('upload_result.html', score=score, total=total)

@app.route('/teacher', methods=['GET','POST'])
def teacher():
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))

    data = load_data()
    if request.method == 'POST':
        data['answer_key']['total_questions'] = int(request.form['total'])
        save_data(data)
        flash("Answer key updated")

    return render_template('teacher.html', submissions=data['submissions'])

if __name__ == '__main__':
    app.run(debug=True)
