from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

# ---------------------------
# DATABASE SETUP
# ---------------------------
DB_PATH = "university.db"

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
            total_paid REAL DEFAULT 0.0
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

# Initialize DB at startup
init_db()

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
    <h2>Courses</h2>
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
        <button type="submit">Register & Pay $25 Registration</button>
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

    # Add user to DB
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT title FROM courses WHERE id=?", (course_id,))
    course = c.fetchone()
    if not course:
        conn.close()
        return "Course not found"

    try:
        c.execute("INSERT INTO users (name, email, phone, enrolled_course) VALUES (?, ?, ?, ?)",
                  (name, email, phone, course[0]))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "Email already registered"

    conn.close()

    # Payment instruction (Lonestar API)
    lonestar_api_key = os.getenv("LONESTAR_API_KEY")
    # Here you would integrate real Lonestar payment API
    payment_message = f"Send registration fee $25 to Lonestar number using API key {lonestar_api_key}"

    return f"Registered successfully! {payment_message}"

# ---------------------------
# ADD SAMPLE COURSES
# ---------------------------
def add_sample_courses():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM courses")
    count = c.fetchone()[0]
    if count == 0:
        sample_courses = [
            ("Computer Science", "Learn CS fundamentals", 200, 6),
            ("Business Administration", "Business degree", 200, 6),
            ("Data Science", "Data analytics and ML", 200, 6),
        ]
        c.executemany("INSERT INTO courses (title, description, price, duration_months) VALUES (?, ?, ?, ?)", sample_courses)
        conn.commit()
    conn.close()

add_sample_courses()

# ---------------------------
# RUN APP
# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
