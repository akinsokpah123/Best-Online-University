from flask import Flask, request, jsonify, render_template_string, redirect, url_for, send_file
import sqlite3
import os
from datetime import datetime, timedelta
import io

app = Flask(__name__)

DB_PATH = "university.db"

# ---------------------------
# DATABASE SETUP
# ---------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Users table
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
    # Courses table
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

# ---------------------------
# SAMPLE COURSES
# ---------------------------
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
        c.executemany("INSERT INTO courses (title, description, price, duration_months) VALUES (?, ?, ?, ?)", courses)
        conn.commit()
    conn.close()

add_sample_courses()

# ---------------------------
# HTML TEMPLATE
# ---------------------------
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

# ---------------------------
# ROUTES
# ---------------------------
@app.route("/healthz")
def healthz():
    return "ok", 200

@app.route("/")
def home():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM courses")
    courses = c.fetchall()
    conn.close()
    return render_template_string(HTML_CODE, courses=courses)

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

    # Check scholarship
    scholarship = 1 if scholarship_code and scholarship_code.lower() == "scholar2025" else 0

    try:
        registration_fee = 25
        tuition_fee = course[1] - registration_fee
        subscription_expiry = datetime.now() + timedelta(days=180)  # 6 months default
        next_payment_due = datetime.now() + timedelta(days=30)  # first installment due in 30 days
        c.execute("""INSERT INTO users 
            (name,email,phone,enrolled_course,registration_fee_paid,tuition_paid,scholarship,subscription_expiry,next_payment_due)
            VALUES (?,?,?,?,?,?,?,?,?)""",
                  (name,email,phone,course[0],registration_fee,0,scholarship,subscription_expiry.strftime("%Y-%m-%d"),
                   next_payment_due.strftime("%Y-%m-%d")))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "Email already registered"
    conn.close()

    lonestar_api_key = os.getenv("LONESTAR_API_KEY")
    payment_message = f"Send registration fee $25 to Lonestar number using API key {lonestar_api_key}"
    return f"Registered successfully! {payment_message}"

@app.route("/pay_installment", methods=["POST"])
def pay_installment():
    email = request.form.get("email")
    amount = float(request.form.get("amount"))
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT tuition_paid, enrolled_course, subscription_expiry FROM users WHERE email=?", (email,))
    user = c.fetchone()
    if not user:
        conn.close()
        return "Student not found"

    tuition_paid = user[0] + amount
    subscription_expiry = datetime.strptime(user[2], "%Y-%m-%d") + timedelta(days=30)  # extend subscription
    c.execute("UPDATE users SET tuition_paid=?, subscription_expiry=?, next_payment_due=? WHERE email=?",
              (tuition_paid, subscription_expiry.strftime("%Y-%m-%d"),
               (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"), email))
    conn.commit()
    conn.close()

    return f"Installment of ${amount} received. Subscription extended to {subscription_expiry.strftime('%Y-%m-%d')}"

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

# ---------------------------
# RUN APP
# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
