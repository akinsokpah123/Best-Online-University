#!/usr/bin/env python3
"""
Akin Online University - All-in-One Flask App
Includes SQLite DB, course setup, registration, Lonestar Mobile Money payments,
student portal, subscription handling, and certificate generation.
"""

from flask import Flask, request, jsonify, render_template_string, send_file
import sqlite3, os, io
from datetime import datetime, timedelta
import subprocess
import sys
import requests

# -------------------------------
# Auto-install requirements if missing
# -------------------------------
required_packages = ["Flask==3.1.1", "gunicorn==23.0.0", "requests==2.31.0"]
for package in required_packages:
    try:
        __import__(package.split("==")[0])
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

app = Flask(__name__)
DB_PATH = "university.db"
LONESTAR_API_KEY = os.getenv("LONESTAR_API_KEY") or "40c621e1cdad417ab0b1b944e2ab9072"

# -------------------------------
# Database setup
# -------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            enrolled_course TEXT,
            registration_fee_paid REAL DEFAULT 0.0,
            tuition_paid REAL DEFAULT 0.0,
            scholarship INTEGER DEFAULT 0,
            subscription_expiry DATE,
            next_payment_due DATE
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            price REAL,
            duration_months INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# -------------------------------
# Sample Courses
# -------------------------------
def add_sample_courses():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM courses")
    if c.fetchone()[0] == 0:
        courses = [
            ("Computer Science", "Learn CS fundamentals", 200, 6),
            ("Business Administration", "Business degree", 200, 6),
            ("Data Science", "Data analytics and ML", 200, 6),
        ]
        c.executemany("INSERT INTO courses (title, description, price, duration_months) VALUES (?,?,?,?)", courses)
        conn.commit()
    conn.close()

add_sample_courses()

# -------------------------------
# HTML Template
# -------------------------------
HTML_CODE = """
<!DOCTYPE html>
<html>
<head>
    <title>Akin Online University</title>
</head>
<body>
<h1>Welcome to Akin Online University</h1>
<h2>Available Courses</h2>
<ul>
{% for course in courses %}
<li>{{course[1]}} - ${{course[3]}} - Duration: {{course[4]}} months</li>
{% endfor %}
</ul>

<h2>Register</h2>
<form action="/register" method="post">
Name: <input type="text" name="name" required><br>
Email: <input type="email" name="email" required><br>
Phone: <input type="text" name="phone" required><br>
Course ID: <input type="number" name="course_id" required><br>
Scholarship Code (optional): <input type="text" name="scholarship"><br>
<button type="submit">Register & Pay $25 Registration</button>
</form>

<h2>Student Portal</h2>
<form action="/student" method="get">
Email: <input type="email" name="email" required><br>
<button type="submit">Access</button>
</form>
</body>
</html>
"""

# -------------------------------
# Health check
# -------------------------------
@app.route("/healthz")
def healthz():
    return "ok", 200

# -------------------------------
# Home Page
# -------------------------------
@app.route("/")
def home():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM courses")
    courses = c.fetchall()
    conn.close()
    return render_template_string(HTML_CODE, courses=courses)

# -------------------------------
# Lonestar MM Payment Verification
# -------------------------------
def verify_payment(phone, amount):
    url = "https://api.lonestarmm.com/payment/verify"
    payload = {"api_key": LONESTAR_API_KEY, "phone": phone, "amount": amount}
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        return data.get("status") == "success"
    except Exception as e:
        print("Lonestar API error:", e)
        return False

# -------------------------------
# Register Student
# -------------------------------
@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    course_id = request.form.get("course_id")
    scholarship_code = request.form.get("scholarship")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT title, price, duration_months FROM courses WHERE id=?", (course_id,))
    course = c.fetchone()
    if not course:
        conn.close()
        return "Course not found"

    scholarship = 1 if scholarship_code and scholarship_code.lower() == "scholar2025" else 0
    registration_fee = 25

    if not verify_payment(phone, registration_fee):
        conn.close()
        return f"Registration fee of ${registration_fee} not verified via Lonestar."

    subscription_expiry = datetime.now() + timedelta(days=180)  # 6 months
    next_payment_due = datetime.now() + timedelta(days=30)

    try:
        c.execute("""INSERT INTO users 
        (name,email,phone,enrolled_course,registration_fee_paid,tuition_paid,scholarship,subscription_expiry,next_payment_due)
        VALUES (?,?,?,?,?,?,?,?,?)""",
                  (name,email,phone,course[0],registration_fee,0,scholarship,
                   subscription_expiry.strftime("%Y-%m-%d"),
                   next_payment_due.strftime("%Y-%m-%d")))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "Email already registered"
    conn.close()
    return f"Registered successfully! You paid ${registration_fee} via Lonestar MM."

# -------------------------------
# Pay Installment
# -------------------------------
@app.route("/pay_installment", methods=["POST"])
def pay_installment():
    email = request.form.get("email")
    amount = float(request.form.get("amount"))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT phone, tuition_paid, subscription_expiry FROM users WHERE email=?", (email,))
    user = c.fetchone()
    if not user:
        conn.close()
        return "Student not found"

    phone = user[0]

    if not verify_payment(phone, amount):
        conn.close()
        return f"Payment of ${amount} not verified via Lonestar."

    tuition_paid = user[1] + amount
    subscription_expiry = datetime.strptime(user[2], "%Y-%m-%d") + timedelta(days=30)

    c.execute("UPDATE users SET tuition_paid=?, subscription_expiry=?, next_payment_due=? WHERE email=?",
              (tuition_paid, subscription_expiry.strftime("%Y-%m-%d"),
               (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"), email))
    conn.commit()
    conn.close()

    return f"Installment of ${amount} received and verified. Subscription extended to {subscription_expiry.strftime('%Y-%m-%d')}"

# -------------------------------
# Student Portal
# -------------------------------
@app.route("/student")
def student_portal():
    email = request.args.get("email")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=?", (email,))
    user = c.fetchone()
    conn.close()
    if not user:
        return "Student not found"

    return f"""
    <h1>Welcome {user[1]}</h1>
    <p>Course: {user[4]}</p>
    <p>Registration Paid: ${user[5]}</p>
    <p>Tuition Paid: ${user[6]}</p>
    <p>Scholarship: {"Yes" if user[7] else "No"}</p>
    <p>Subscription Expiry: {user[8]}</p>
    <p>Next Payment Due: {user[9]}</p>
    <form action="/pay_installment" method="post">
        Amount: <input type="number" name="amount" step="0.01" required><br>
        <input type="hidden" name="email" value="{user[2]}">
        <button type="submit">Pay Installment</button>
    </form>
    <a href='/certificate?email={email}'>Download Certificate</a>
    """

# -------------------------------
# Certificate Generation
# -------------------------------
@app.route("/certificate")
def certificate():
    email = request.args.get("email")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, enrolled_course FROM users WHERE email=?", (email,))
    user = c.fetchone()
    conn.close()
    if not user:
        return "Student not found"

    certificate_text = f"Certificate of Completion\n\nThis is to certify that {user[0]} completed the course {user[1]}."
    return send_file(io.BytesIO(certificate_text.encode()), attachment_filename="certificate.txt", as_attachment=True)

# -------------------------------
# Run App
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
