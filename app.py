from flask import Flask, request, jsonify, render_template_string, send_file
import sqlite3
import requests
import os
import pdfkit
from datetime import datetime, timedelta

app = Flask(__name__)

# ======================
# CONFIG
# ======================
LONESTAR_API_KEY = os.getenv("LONESTAR_API_KEY")
DB_FILE = "akin_online_university.db"

# ======================
# DATABASE SETUP
# ======================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            phone TEXT,
            registration_date TEXT,
            subscription_end TEXT,
            total_paid REAL DEFAULT 0
        )
    """)
    # Courses table
    c.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            price REAL,
            duration_months INTEGER
        )
    """)
    # Payments table
    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            course_id INTEGER,
            amount REAL,
            payment_date TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

# Initialize DB before first request
@app.before_first_request
def setup():
    init_db()

# ======================
# HELPER FUNCTIONS
# ======================
def make_payment(phone, amount):
    """Call Lonestar API for payment"""
    url = "https://api.lonestarmobile.com/payment"
    headers = {"Authorization": f"Bearer {LONESTAR_API_KEY}"}
    data = {"phone": phone, "amount": amount}
    response = requests.post(url, json=data, headers=headers)
    return response.json()  # Expect {"status": "success"} or {"status": "failed"}

# ======================
# ROUTES
# ======================
@app.route("/healthz")
def healthz():
    return "ok", 200

@app.route("/")
def home():
    return render_template_string("""
    <h1>Welcome to Akin Online University</h1>
    <p>Courses, subscriptions, certificates all online!</p>
    """)

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    registration_date = datetime.now().strftime("%Y-%m-%d")
    subscription_end = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")  # default 6 months
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (name,email,phone,registration_date,subscription_end) VALUES (?,?,?,?,?)",
                  (name,email,phone,registration_date,subscription_end))
        conn.commit()
        user_id = c.lastrowid
        return jsonify({"status":"success","user_id":user_id})
    except sqlite3.IntegrityError:
        return jsonify({"status":"error","message":"Email already registered"})
    finally:
        conn.close()

@app.route("/enroll", methods=["POST"])
def enroll():
    data = request.json
    user_id = data.get("user_id")
    course_id = data.get("course_id")
    amount = data.get("amount")
    phone = data.get("phone")

    payment_result = make_payment(phone, amount)
    if payment_result.get("status") != "success":
        return jsonify({"status":"failed","message":"Payment failed"})

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO payments (user_id, course_id, amount,payment_date,status) VALUES (?,?,?,?,?)",
              (user_id, course_id, amount, datetime.now().strftime("%Y-%m-%d"), "success"))
    conn.commit()
    conn.close()
    return jsonify({"status":"success","message":"Enrollment successful"})

@app.route("/certificate/<int:user_id>/<int:course_id>")
def certificate(user_id, course_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name,email FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    c.execute("SELECT name FROM courses WHERE id=?", (course_id,))
    course = c.fetchone()
    conn.close()

    if not user or not course:
        return "User or Course not found",404

    html = f"""
    <h1>Certificate of Completion</h1>
    <p>This certifies that {user[0]} ({user[1]}) has completed the course <b>{course[0]}</b> successfully.</p>
    <p>Date: {datetime.now().strftime('%Y-%m-%d')}</p>
    """
    pdf_file = f"certificate_{user_id}_{course_id}.pdf"
    pdfkit.from_string(html, pdf_file)
    return send_file(pdf_file, as_attachment=True)

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
