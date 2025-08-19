# app.py
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for
import sqlite3
import os
import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
import requests

# =========================
# CONFIGURATION
# =========================
app = Flask(__name__)
DATABASE = 'university.db'
LONESTAR_API_KEY = os.getenv('LONESTAR_API_KEY')  # Set in Render environment variables
ADMIN_PASSWORD = "admin123"  # Change this to a secure password

# =========================
# DATABASE SETUP
# =========================
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    # Students table
    c.execute('''CREATE TABLE IF NOT EXISTS students (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT,
                 email TEXT,
                 phone TEXT,
                 level TEXT,
                 registration_fee_paid INTEGER DEFAULT 0,
                 course_fee_paid INTEGER DEFAULT 0,
                 enrollment_date TEXT
                 )''')
    # Courses table
    c.execute('''CREATE TABLE IF NOT EXISTS courses (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT,
                 description TEXT,
                 fee INTEGER
                 )''')
    # Payments table
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 student_id INTEGER,
                 amount INTEGER,
                 reference TEXT,
                 status TEXT,
                 date TEXT
                 )''')
    conn.commit()
    conn.close()

init_db()

# =========================
# HTML TEMPLATES
# =========================
HOME_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Akin Online University</title>
</head>
<body>
<h1>Welcome to Akin Online University</h1>
<a href="/courses">View Courses</a><br>
<a href="/register">Register</a>
</body>
</html>
"""

COURSES_HTML = """
<!DOCTYPE html>
<html>
<head><title>Courses</title></head>
<body>
<h1>Courses</h1>
<ul>
{% for course in courses %}
<li>{{ course[1] }} - Fee: ${{ course[3] }} <a href="/enroll/{{ course[0] }}">Enroll</a></li>
{% endfor %}
</ul>
<a href="/">Home</a>
</body>
</html>
"""

REGISTER_HTML = """
<!DOCTYPE html>
<html>
<head><title>Register</title></head>
<body>
<h1>Student Registration</h1>
<form action="/register" method="post">
Name: <input type="text" name="name" required><br>
Email: <input type="email" name="email" required><br>
Phone: <input type="text" name="phone" required><br>
Level: 
<select name="level">
<option value="undergraduate">Undergraduate</option>
<option value="postgraduate">Postgraduate</option>
</select><br>
<input type="submit" value="Register">
</form>
<a href="/">Home</a>
</body>
</html>
"""

# =========================
# ROUTES
# =========================
@app.route('/')
def home():
    return render_template_string(HOME_HTML)

@app.route('/courses')
def courses():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM courses")
    courses = c.fetchall()
    conn.close()
    return render_template_string(COURSES_HTML, courses=courses)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        level = request.form['level']
        enrollment_date = str(datetime.date.today())
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO students (name,email,phone,level,enrollment_date) VALUES (?,?,?,?,?)",
                  (name,email,phone,level,enrollment_date))
        conn.commit()
        conn.close()
        return f"Registered {name}! <a href='/courses'>View Courses</a>"
    return render_template_string(REGISTER_HTML)

# =========================
# ENROLLMENT & PAYMENT
# =========================
@app.route('/enroll/<int:course_id>')
def enroll(course_id):
    # For simplicity, pick student_id=1 (demo), replace with real login system
    student_id = 1
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT fee FROM courses WHERE id=?", (course_id,))
    course = c.fetchone()
    if not course:
        return "Course not found"
    fee = course[0]
    # Initiate Lonestar payment
    payment_ref = f"UNI{student_id}{course_id}{int(datetime.datetime.now().timestamp())}"
    payment_data = {
        "api_key": LONESTAR_API_KEY,
        "amount": fee,
        "msisdn": "231XXXXXXXXX",  # Replace with student phone
        "reference": payment_ref
    }
    # Demo: simulate API request
    # resp = requests.post("https://lonestar.api/pay", data=payment_data)
    # Here we just assume success
    c.execute("INSERT INTO payments (student_id, amount, reference, status, date) VALUES (?,?,?,?,?)",
              (student_id, fee, payment_ref, "paid", str(datetime.datetime.now())))
    conn.commit()
    conn.close()
    return f"Enrolled and paid ${fee} for course {course_id}! Reference: {payment_ref}"

# =========================
# PDF GENERATION
# =========================
@app.route('/certificate/<int:student_id>')
def certificate(student_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT name,level FROM students WHERE id=?", (student_id,))
    student = c.fetchone()
    conn.close()
    if not student:
        return "Student not found"
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 750, "Akin Online University")
    p.drawString(100, 720, f"Certificate of Enrollment")
    p.drawString(100, 690, f"Student: {student[0]}")
    p.drawString(100, 660, f"Level: {student[1]}")
    p.drawString(100, 630, f"Date: {datetime.date.today()}")
    p.showPage()
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="certificate.pdf", mimetype='application/pdf')

# =========================
# ADMIN DASHBOARD
# =========================
@app.route('/admin')
def admin_home():
    return """
    <h1>Admin Dashboard</h1>
    <a href='/admin/courses'>Manage Courses</a>
    """

@app.route('/admin/courses', methods=['GET', 'POST'])
def admin_courses():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        desc = request.form['desc']
        fee = int(request.form['fee'])
        c.execute("INSERT INTO courses (name, description, fee) VALUES (?,?,?)", (name, desc, fee))
        conn.commit()
    c.execute("SELECT * FROM courses")
    courses = c.fetchall()
    conn.close()
    course_list = "<ul>"
    for course in courses:
        course_list += f"<li>{course[1]} - ${course[3]}</li>"
    course_list += "</ul>"
    return f"""
    <h1>Manage Courses</h1>
    {course_list}
    <form method='post'>
    Name: <input type='text' name='name'><br>
    Description: <input type='text' name='desc'><br>
    Fee: <input type='number' name='fee'><br>
    <input type='submit' value='Add Course'>
    </form>
    """

# =========================
# HEALTH CHECK
# =========================
@app.route('/healthz')
def healthz():
    return "ok", 200

# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)

# =========================
# REQUIREMENTS (requirements.txt content)
# =========================
"""
Flask==3.1.1
requests==2.31.0
reportlab==4.0.0
"""
