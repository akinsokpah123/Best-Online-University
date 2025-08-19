from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
import sqlite3
import os
import hashlib
import datetime
import requests

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

DATABASE = 'university.db'
LONESTAR_API_KEY = '40c621e1cdad417ab0b1b944e2ab9072'

# ================== Database Setup ==================
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    # Students table
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            enrolled_courses TEXT,
            registration_date TEXT,
            scholarship BOOLEAN DEFAULT 0
        )
    ''')
    # Courses table
    c.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL,
            duration_months INTEGER DEFAULT 6,
            is_free BOOLEAN DEFAULT 0
        )
    ''')
    # Payments table
    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            course_id INTEGER,
            amount REAL,
            paid BOOLEAN DEFAULT 0,
            payment_date TEXT,
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(course_id) REFERENCES courses(id)
        )
    ''')
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ================== Helper Functions ==================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_payment(student_id, course_id, amount):
    """
    Simulate Lonestar Mobile Money verification
    In reality, this should call Lonestar API with API key
    """
    # Placeholder: always return True for demo
    return True

# ================== Routes ==================
HTML_HOME = """
<!DOCTYPE html>
<html>
<head>
  <title>Akin Online University</title>
  <style>
    body { font-family: Arial, sans-serif; background:#f4f4f4; }
    #container { width: 80%; margin:auto; padding:20px; }
    a { text-decoration:none; color:#333; }
    .btn { padding:10px 15px; background:#4CAF50;color:white;border-radius:5px; }
    .btn:hover { background:#45a049; }
  </style>
</head>
<body>
<div id="container">
<h1>Welcome to Akin Online University 🎓</h1>
<p><a href="/register" class="btn">Register</a> | <a href="/login" class="btn">Login</a> | <a href="/courses" class="btn">View Courses</a></p>
</div>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_HOME)

# ===== Registration =====
HTML_REGISTER = """
<!DOCTYPE html>
<html>
<head>
<title>Register - Akin Online University</title>
</head>
<body>
<h2>Register</h2>
<form method="POST">
Name: <input type="text" name="name" required><br>
Email: <input type="email" name="email" required><br>
Password: <input type="password" name="password" required><br>
<input type="submit" value="Register">
</form>
<p>{{ message }}</p>
</body>
</html>
"""

@app.route("/register", methods=["GET","POST"])
def register():
    message = ""
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        password = hash_password(request.form['password'])
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO students (name,email,password,registration_date) VALUES (?,?,?,?)",
                      (name,email,password,str(datetime.date.today())))
            conn.commit()
            message = "Registered successfully! Please login."
        except sqlite3.IntegrityError:
            message = "Email already exists."
        conn.close()
    return render_template_string(HTML_REGISTER, message=message)

# ===== Login =====
HTML_LOGIN = """
<!DOCTYPE html>
<html>
<head><title>Login</title></head>
<body>
<h2>Login</h2>
<form method="POST">
Email: <input type="email" name="email" required><br>
Password: <input type="password" name="password" required><br>
<input type="submit" value="Login">
</form>
<p>{{ message }}</p>
</body>
</html>
"""

@app.route("/login", methods=["GET","POST"])
def login():
    message = ""
    if request.method == "POST":
        email = request.form['email']
        password = hash_password(request.form['password'])
        conn = get_db_connection()
        student = conn.execute("SELECT * FROM students WHERE email=? AND password=?", (email,password)).fetchone()
        conn.close()
        if student:
            session['student_id'] = student['id']
            session['student_name'] = student['name']
            return redirect(url_for('dashboard'))
        else:
            message = "Invalid credentials"
    return render_template_string(HTML_LOGIN, message=message)

# ===== Dashboard =====
HTML_DASHBOARD = """
<!DOCTYPE html>
<html>
<head><title>Dashboard</title></head>
<body>
<h2>Welcome, {{ name }}!</h2>
<p><a href="/courses">View Courses</a> | <a href="/logout">Logout</a></p>
</body>
</html>
"""

@app.route("/dashboard")
def dashboard():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    return render_template_string(HTML_DASHBOARD, name=session['student_name'])

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))

# ===== Courses =====
HTML_COURSES = """
<!DOCTYPE html>
<html>
<head><title>Courses</title></head>
<body>
<h2>Available Courses</h2>
<ul>
{% for course in courses %}
<li>{{ course['name'] }} - {% if course['is_free'] %}Free{% else %}${{ course['price'] }}{% endif %} 
{% if not course['is_free'] %}<a href="/pay/{{ course['id'] }}" class="btn">Enroll</a>{% endif %}</li>
{% endfor %}
</ul>
<p><a href="/dashboard">Back to Dashboard</a></p>
</body>
</html>
"""

@app.route("/courses")
def courses():
    conn = get_db_connection()
    courses = conn.execute("SELECT * FROM courses").fetchall()
    conn.close()
    return render_template_string(HTML_COURSES, courses=courses)

# ===== Payment =====
HTML_PAY = """
<!DOCTYPE html>
<html>
<head><title>Pay</title></head>
<body>
<h2>Pay for {{ course['name'] }}</h2>
<p>Price: ${{ course['price'] }}</p>
<form method="POST">
Mobile Money Number: <input type="text" name="number" placeholder="e.g., 231887716973" required><br>
<input type="submit" value="Pay">
</form>
<p>{{ message }}</p>
<p><a href="/courses">Back to Courses</a></p>
</body>
</html>
"""

@app.route("/pay/<int:course_id>", methods=["GET","POST"])
def pay(course_id):
    if 'student_id' not in session:
        return redirect(url_for('login'))
    message = ""
    conn = get_db_connection()
    course = conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
    if request.method=="POST":
        number = request.form['number']
        # Simulate Lonestar payment verification
        if verify_payment(session['student_id'], course_id, course['price']):
            conn.execute("INSERT INTO payments (student_id,course_id,amount,paid,payment_date) VALUES (?,?,?,?,?)",
                         (session['student_id'],course_id,course['price'],1,str(datetime.date.today())))
            conn.commit()
            message = "Payment successful! You are enrolled."
        else:
            message = "Payment failed. Try again."
    conn.close()
    return render_template_string(HTML_PAY, course=course, message=message)

# ================== Start App ==================
if __name__ == "__main__":
    init_db()
    # Add sample courses if not exist
    conn = get_db_connection()
    courses_exist = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    if courses_exist==0:
        conn.execute("INSERT INTO courses (name,description,price,is_free) VALUES ('Computer Science','BSc CS Course',200,0)")
        conn.execute("INSERT INTO courses (name,description,price,is_free) VALUES ('Mathematics','BSc Math Course',0,1)")
        conn.commit()
    conn.close()
    app.run(host="0.0.0.0", port=10000, debug=True)
