# ===============================
# Akin Online University
# All-in-one deployable Flask App
# ===============================

import os
import sqlite3
from flask import Flask, request, jsonify, render_template_string, send_file
from datetime import datetime, timedelta
import requests
import pdfkit

# -----------------------
# Setup Flask
# -----------------------
app = Flask(__name__)

# -----------------------
# Lonestar API
# -----------------------
LONESTAR_API_KEY = os.getenv("LONESTAR_API_KEY") or "40c621e1cdad417ab0b1b944e2ab9072"

# -----------------------
# SQLite Database
# -----------------------
DB_NAME = "university.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Students table
    c.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        degree TEXT,
        registered_on TEXT,
        subscription_end TEXT,
        scholarship INTEGER DEFAULT 0
    )
    """)
    
    # Courses table
    c.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        level TEXT,
        price REAL
    )
    """)
    
    # Enrollments table
    c.execute("""
    CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        course_id INTEGER,
        start_date TEXT,
        end_date TEXT,
        paid REAL DEFAULT 0,
        completed INTEGER DEFAULT 0,
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(course_id) REFERENCES courses(id)
    )
    """)
    
    # Payments table
    c.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        amount REAL,
        payment_method TEXT,
        payment_date TEXT,
        verified INTEGER DEFAULT 0,
        FOREIGN KEY(student_id) REFERENCES students(id)
    )
    """)
    
    conn.commit()
    conn.close()

init_db()

# -----------------------
# Templates
# -----------------------
HOME_PAGE = """
<!DOCTYPE html>
<html>
<head>
<title>Akin Online University</title>
<style>
body {font-family: Arial,sans-serif; background:#f4f4f4; padding:20px;}
.container {max-width:900px; margin:auto; background:white; padding:20px; border-radius:10px;}
input, select {width:100%; padding:10px; margin:5px 0;}
button {padding:10px 20px; background:#4CAF50; color:white; border:none; cursor:pointer;}
button:hover {background:#45a049;}
</style>
</head>
<body>
<div class="container">
<h1>Welcome to Akin Online University 🎓</h1>
<p>Enroll for free undergraduate courses or pay for advanced courses.</p>

<h2>Register Student</h2>
<form id="registerForm">
<input type="text" id="full_name" placeholder="Full Name" required/>
<input type="email" id="email" placeholder="Email" required/>
<input type="password" id="password" placeholder="Password" required/>
<select id="degree">
<option value="undergraduate">Undergraduate (Free First Course)</option>
<option value="graduate">Graduate</option>
<option value="postgraduate">Postgraduate</option>
</select>
<button type="button" onclick="register()">Register</button>
</form>

<h2>Enroll in Course</h2>
<form id="enrollForm">
<input type="number" id="student_id" placeholder="Student ID" required/>
<input type="number" id="course_id" placeholder="Course ID" required/>
<button type="button" onclick="enroll()">Enroll</button>
</form>

<div id="messages"></div>
</div>
<script>
async function register(){
    let data = {
        full_name: document.getElementById('full_name').value,
        email: document.getElementById('email').value,
        password: document.getElementById('password').value,
        degree: document.getElementById('degree').value
    };
    let res = await fetch('/register', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    let json = await res.json();
    document.getElementById('messages').innerText = JSON.stringify(json);
}

async function enroll(){
    let data = {
        student_id: document.getElementById('student_id').value,
        course_id: document.getElementById('course_id').value
    };
    let res = await fetch('/enroll', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    let json = await res.json();
    document.getElementById('messages').innerText = JSON.stringify(json);
}
</script>
</body>
</html>
"""

# -----------------------
# Routes
# -----------------------
@app.route("/")
def home():
    return render_template_string(HOME_PAGE)

@app.route("/healthz")
def healthz():
    return "ok", 200

# -----------------------
# Student Registration
# -----------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    full_name = data.get("full_name")
    email = data.get("email")
    password = data.get("password")
    degree = data.get("degree")
    registered_on = datetime.utcnow().isoformat()
    subscription_end = (datetime.utcnow() + timedelta(days=180)).isoformat()  # 6 months default
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO students (full_name,email,password,degree,registered_on,subscription_end) VALUES (?,?,?,?,?,?)",
                  (full_name,email,password,degree,registered_on,subscription_end))
        conn.commit()
        student_id = c.lastrowid
        conn.close()
        return jsonify({"status":"success","student_id":student_id})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"status":"error","message":"Email already registered"}),400

# -----------------------
# Enrollment
# -----------------------
@app.route("/enroll", methods=["POST"])
def enroll():
    data = request.json
    student_id = int(data.get("student_id"))
    course_id = int(data.get("course_id"))
    
    start_date = datetime.utcnow().isoformat()
    end_date = (datetime.utcnow() + timedelta(days=180)).isoformat()
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO enrollments (student_id,course_id,start_date,end_date) VALUES (?,?,?,?)",
              (student_id,course_id,start_date,end_date))
    conn.commit()
    conn.close()
    
    # Mock payment request to Lonestar API
    # Normally here you would call their API with proper authentication
    payment_status = "pending"  # Assume payment pending
    return jsonify({"status":"enrolled","payment_status":payment_status})

# -----------------------
# Run app
# -----------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
