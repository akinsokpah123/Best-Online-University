import os
import sqlite3
from flask import Flask, request, jsonify, render_template_string, send_file
from datetime import datetime, timedelta
import io
from reportlab.pdfgen import canvas
import requests

app = Flask(__name__)

# ==========================
# Configuration
# ==========================
LONESTAR_API_KEY = os.getenv("LONESTAR_API_KEY")
DB_FILE = "university.db"

# ==========================
# Database Setup
# ==========================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            phone TEXT UNIQUE,
            registration_date TEXT,
            subscription_end TEXT,
            total_paid REAL DEFAULT 0
        )
    """)
    # Courses table
    c.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            price REAL,
            duration_months INTEGER
        )
    """)
    # Enrollments table
    c.execute("""
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            course_id INTEGER,
            enrolled_on TEXT,
            paid_amount REAL DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(course_id) REFERENCES courses(id)
        )
    """)
    conn.commit()
    conn.close()

# Initialize DB
init_db()

# ==========================
# Helper Functions
# ==========================
def add_sample_courses():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM courses")
    if c.fetchone()[0] == 0:
        courses = [
            ("Computer Science", "BSc in Computer Science", 200, 6),
            ("Business Administration", "BBA Degree", 200, 6),
            ("Mathematics", "BSc in Mathematics", 200, 6),
        ]
        c.executemany("INSERT INTO courses (title, description, price, duration_months) VALUES (?,?,?,?)", courses)
        conn.commit()
    conn.close()

add_sample_courses()

def generate_certificate(user_name, course_title):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(100, 750, "Akin Online University")
    c.setFont("Helvetica", 18)
    c.drawString(100, 700, f"Certificate of Completion")
    c.setFont("Helvetica", 14)
    c.drawString(100, 650, f"This certifies that {user_name}")
    c.drawString(100, 630, f"has successfully completed the course {course_title}")
    c.drawString(100, 610, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    c.save()
    buffer.seek(0)
    return buffer

def process_lonestar_payment(phone, amount):
    # This is a simulation. Replace with real Lonestar API endpoint
    url = "https://api.lonestarmobile.com/payment"
    headers = {"Authorization": f"Bearer {LONESTAR_API_KEY}"}
    data = {"phone": phone, "amount": amount}
    # response = requests.post(url, json=data, headers=headers)
    # For now, we simulate a success:
    return {"status": "success", "message": f"${amount} paid from {phone}"}

# ==========================
# Routes
# ==========================
HTML_CODE = """
<!DOCTYPE html>
<html>
<head>
  <title>Akin Online University</title>
  <style>
    body { font-family: Arial, sans-serif; background: #f4f4f4; }
    .container { width: 80%; margin: 20px auto; background: white; padding: 20px; border-radius: 12px; }
    h2 { text-align: center; }
    input, select { padding: 8px; margin: 5px 0; width: 100%; }
    button { padding: 10px; margin-top: 10px; background: #4CAF50; color: white; border: none; border-radius: 6px; cursor: pointer; }
    button:hover { background: #45a049; }
    .course { border:1px solid #ccc; padding:10px; margin:10px 0; border-radius:6px; }
  </style>
</head>
<body>
  <div class="container">
    <h2>🎓 Akin Online University</h2>

    <h3>Register</h3>
    <input id="name" placeholder="Full Name"/>
    <input id="email" placeholder="Email"/>
    <input id="phone" placeholder="Phone"/>
    <button onclick="register()">Register ($25 Registration Fee)</button>

    <h3>Available Courses</h3>
    <div id="courses"></div>

    <h3>Enroll in Course</h3>
    <input id="enroll_email" placeholder="Your Email"/>
    <select id="course_select"></select>
    <button onclick="enroll()">Enroll & Pay</button>

    <h3>Download Certificate</h3>
    <input id="cert_email" placeholder="Your Email"/>
    <select id="cert_course"></select>
    <button onclick="downloadCert()">Download Certificate</button>
  </div>

<script>
async function register() {
    let name = document.getElementById('name').value;
    let email = document.getElementById('email').value;
    let phone = document.getElementById('phone').value;
    let res = await fetch('/register', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({name,email,phone})
    });
    let data = await res.json();
    alert(data.message);
}

async function loadCourses() {
    let res = await fetch('/courses');
    let data = await res.json();
    let coursesDiv = document.getElementById('courses');
    let select = document.getElementById('course_select');
    let certSelect = document.getElementById('cert_course');
    coursesDiv.innerHTML = '';
    data.forEach(c => {
        coursesDiv.innerHTML += `<div class="course"><b>${c.title}</b>: ${c.description} - $${c.price} for ${c.duration_months} months</div>`;
        select.innerHTML += `<option value="${c.id}">${c.title}</option>`;
        certSelect.innerHTML += `<option value="${c.id}">${c.title}</option>`;
    });
}
loadCourses();

async function enroll() {
    let email = document.getElementById('enroll_email').value;
    let course_id = document.getElementById('course_select').value;
    let res = await fetch('/enroll', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({email,course_id})
    });
    let data = await res.json();
    alert(data.message);
}

function downloadCert() {
    let email = document.getElementById('cert_email').value;
    let course_id = document.getElementById('cert_course').value;
    window.open(`/certificate?email=${email}&course_id=${course_id}`);
}
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_CODE)

@app.route("/healthz")
def healthz():
    return "ok", 200

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    if not name or not email or not phone:
        return jsonify({"message":"All fields required"}),400

    # Process $25 registration via Lonestar
    payment = process_lonestar_payment(phone, 25)
    if payment["status"] != "success":
        return jsonify({"message":"Payment failed"}),400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (name,email,phone,registration_date,total_paid) VALUES (?,?,?,?,?)",
                  (name,email,phone,datetime.now().strftime('%Y-%m-%d'),25))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"message":"User already registered"}),400
    conn.close()
    return jsonify({"message":"Registration successful! $25 paid."})

@app.route("/courses")
def courses():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id,title,description,price,duration_months FROM courses")
    rows = c.fetchall()
    conn.close()
    data = [{"id":r[0],"title":r[1],"description":r[2],"price":r[3],"duration_months":r[4]} for r in rows]
    return jsonify(data)

@app.route("/enroll", methods=["POST"])
def enroll():
    data = request.json
    email = data.get("email")
    course_id = data.get("course_id")
    if not email or not course_id:
        return jsonify({"message":"Email and course_id required"}),400
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id,phone,total_paid FROM users WHERE email=?", (email,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({"message":"User not found"}),404
    user_id, phone, total_paid = user

    # Check if already enrolled
    c.execute("SELECT id FROM enrollments WHERE user_id=? AND course_id=?", (user_id, course_id))
    if c.fetchone():
        conn.close()
        return jsonify({"message":"Already enrolled"}),400

    # Get course price
    c.execute("SELECT price FROM courses WHERE id=?", (course_id,))
    price = c.fetchone()[0]

    # Pay via Lonestar
    payment = process_lonestar_payment(phone, price)
    if payment["status"] != "success":
        return jsonify({"message":"Payment failed"}),400

    # Record enrollment
    c.execute("INSERT INTO enrollments (user_id, course_id,enrolled_on,paid_amount) VALUES (?,?,?,?)",
              (user_id, course_id, datetime.now().strftime('%Y-%m-%d'), price))
    # Update total_paid
    total_paid += price
    c.execute("UPDATE users SET total_paid=? WHERE id=?", (total_paid,user_id))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Enrolled successfully! Paid ${price} via Lonestar."})

@app.route("/certificate")
def certificate():
    email = request.args.get("email")
    course_id = request.args.get("course_id")
    if not email or not course_id:
        return "Missing parameters",400
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT u.name, c.title FROM users u JOIN enrollments e ON u.id=e.user_id JOIN courses c ON c.id=e.course_id WHERE u.email=? AND c.id=?",(email,course_id))
    row = c.fetchone()
    conn.close()
    if not row:
        return "Enrollment not found",404
    user_name, course_title = row
    pdf = generate_certificate(user_name, course_title)
    return send_file(pdf, as_attachment=True, download_name=f"{course_title}_certificate.pdf", mimetype='application/pdf')

# ==========================
# Run App
# ==========================
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
