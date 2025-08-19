# app.py
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, send_file
import sqlite3
import os
import uuid
import datetime
import requests
from fpdf import FPDF

# ---------- Configuration ----------
app = Flask(__name__)
DATABASE = "university.db"
LONESTAR_API_KEY = os.getenv("LONESTAR_API_KEY")  # your Lonestar API key
REGISTRATION_FEE = 25
TOTAL_TUITION = 200

# ---------- Database setup ----------
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    # Users table
    c.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        registration_paid INTEGER DEFAULT 0,
        tuition_paid INTEGER DEFAULT 0,
        enrollment_date TEXT,
        scholarship INTEGER DEFAULT 0,
        credits INTEGER DEFAULT 0,
        grade REAL DEFAULT 0.0
    )
    """)
    # Courses table
    c.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        duration_months INTEGER
    )
    """)
    # Payments table
    c.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        amount REAL,
        date TEXT,
        payment_type TEXT,
        reference TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- Helper functions ----------
def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(query, args)
    rv = c.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def make_payment(student_id, amount):
    """Simulate Lonestar Mobile Money payment"""
    reference = str(uuid.uuid4())
    query_db("INSERT INTO payments (student_id, amount, date, payment_type, reference) VALUES (?, ?, ?, ?, ?)",
             (student_id, amount, datetime.datetime.now().isoformat(), "mobile_money", reference))
    return True, reference

def generate_certificate(student_name, course_title):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Akin Online University", ln=True, align="C")
    pdf.cell(0, 10, f"Certificate of Completion", ln=True, align="C")
    pdf.ln(20)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 10, f"This is to certify that {student_name} has successfully completed the course '{course_title}'.")
    filename = f"certificate_{uuid.uuid4().hex}.pdf"
    pdf.output(filename)
    return filename

def generate_transcript(student):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Akin Online University", ln=True, align="C")
    pdf.cell(0, 10, "Official Transcript", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Student Name: {student[1]}", ln=True)
    pdf.cell(0, 10, f"Email: {student[2]}", ln=True)
    pdf.cell(0, 10, f"Enrollment Date: {student[6]}", ln=True)
    pdf.cell(0, 10, f"Credits Earned: {student[8]}", ln=True)
    pdf.cell(0, 10, f"GPA: {student[9]}", ln=True)
    filename = f"transcript_{uuid.uuid4().hex}.pdf"
    pdf.output(filename)
    return filename

# ---------- Routes ----------
@app.route("/healthz")
def healthz():
    return "ok", 200

@app.route("/")
def home():
    courses = query_db("SELECT id, title, description, duration_months FROM courses")
    html = """
    <h1>Welcome to Akin Online University</h1>
    <a href='/register'>Register</a> | <a href='/login'>Login</a>
    <h2>Courses Available</h2>
    {% for c in courses %}
        <div>
            <h3>{{c[1]}}</h3>
            <p>{{c[2]}}</p>
            <p>Duration: {{c[3]}} months</p>
        </div>
    {% endfor %}
    """
    return render_template_string(html, courses=courses)

@app.route("/register", methods=["GET", "POST"])
def register():
    html = """
    <h1>Student Registration</h1>
    <form method='post'>
        Name: <input name='name'><br>
        Email: <input name='email'><br>
        Password: <input type='password' name='password'><br>
        <button type='submit'>Register & Pay $25</button>
    </form>
    """
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        query_db("INSERT INTO students (name, email, password, enrollment_date) VALUES (?, ?, ?, ?)",
                 (name, email, password, datetime.datetime.now().isoformat()))
        student = query_db("SELECT id FROM students WHERE email=?", (email,), one=True)
        success, ref = make_payment(student[0], REGISTRATION_FEE)
        query_db("UPDATE students SET registration_paid=1 WHERE id=?", (student[0],))
        return f"Registered successfully! Registration payment ref: {ref} <a href='/'>Home</a>"
    return render_template_string(html)

@app.route("/login", methods=["GET", "POST"])
def login():
    html = """
    <h1>Student Login</h1>
    <form method='post'>
        Email: <input name='email'><br>
        Password: <input type='password' name='password'><br>
        <button type='submit'>Login</button>
    </form>
    """
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        student = query_db("SELECT * FROM students WHERE email=? AND password=?", (email, password), one=True)
        if student:
            return redirect(url_for("dashboard", student_id=student[0]))
        return "Invalid login"
    return render_template_string(html)

@app.route("/dashboard/<int:student_id>")
def dashboard(student_id):
    student = query_db("SELECT * FROM students WHERE id=?", (student_id,), one=True)
    courses = query_db("SELECT id, title FROM courses")
    html = """
    <h1>Welcome {{student[1]}}</h1>
    <p>Registration Paid: {{student[4]}}</p>
    <p>Tuition Paid: {{student[5]}}</p>
    <p>Scholarship Eligible: {{student[7]}}</p>
    <h2>Courses</h2>
    {% for c in courses %}
        <div>
            <p>{{c[1]}} - <a href='/enroll/{{student[0]}}/{{c[0]}}'>Enroll</a></p>
        </div>
    {% endfor %}
    <h2>Certificates & Transcripts</h2>
    <a href='/certificate/{{student[0]}}'>Download Certificate</a><br>
    <a href='/transcript/{{student[0]}}'>Download Transcript</a>
    """
    return render_template_string(html, student=student, courses=courses)

@app.route("/enroll/<int:student_id>/<int:course_id>")
def enroll(student_id, course_id):
    success, ref = make_payment(student_id, TOTAL_TUITION)
    query_db("UPDATE students SET tuition_paid=1, credits=credits+30, grade=grade+4.0, scholarship=1 WHERE id=?", (student_id,))
    course = query_db("SELECT title FROM courses WHERE id=?", (course_id,), one=True)
    return f"Enrolled in {course[0]} successfully! Tuition payment ref: {ref} <a href='/dashboard/{student_id}'>Back</a>"

@app.route("/certificate/<int:student_id>")
def certificate(student_id):
    student = query_db("SELECT name FROM students WHERE id=?", (student_id,), one=True)
    course = "Any Course"  # simplified
    filename = generate_certificate(student[0], course)
    return send_file(filename, as_attachment=True)

@app.route("/transcript/<int:student_id>")
def transcript(student_id):
    student = query_db("SELECT * FROM students WHERE id=?", (student_id,), one=True)
    filename = generate_transcript(student)
    return send_file(filename, as_attachment=True)

@app.route("/admin/add_course", methods=["GET", "POST"])
def add_course():
    html = """
    <h1>Add Course (Admin)</h1>
    <form method='post'>
        Title: <input name='title'><br>
        Description: <input name='description'><br>
        Duration (months): <input name='duration'><br>
        <button type='submit'>Add Course</button>
    </form>
    """
    if request.method == "POST":
        title = request.form['title']
        description = request.form['description']
        duration = int(request.form['duration'])
        query_db("INSERT INTO courses (title, description, duration_months) VALUES (?, ?, ?)",
                 (title, description, duration))
        return "Course added! <a href='/'>Home</a>"
    return render_template_string(html)

# ---------- Run App ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
