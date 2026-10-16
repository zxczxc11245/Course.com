import sqlite3
from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "my_secret_key_123"


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (course_id) REFERENCES courses(id),
            UNIQUE(user_id, course_id)
        )
    """)
    conn.commit()
    conn.close()


init_db()


# Home

@app.route("/")
def index():
    conn = get_db_connection()
    courses = conn.execute("SELECT * FROM courses").fetchall()
    conn.close()
    return render_template("index.html", courses=courses)


@app.route("/course/<int:course_id>")
def course_detail(course_id):
    return render_template(f"k{course_id}.html")


# Course Enrollment

@app.route("/enroll/<int:course_id>", methods=["POST"])
def enroll(course_id):
    if not session.get("user"):
        return redirect(url_for("login"))

    conn = get_db_connection()

    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (session["user"],)
    ).fetchone()

    conn.execute(
        "INSERT OR IGNORE INTO enrollments (user_id, course_id) VALUES (?, ?)",
        (user["id"], course_id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("index"))


# Login

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user"] = user["username"]
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")


# Sign Up

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            return render_template("signup.html", error="Passwords do not match")

        conn = get_db_connection()

        existing_user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if existing_user:
            conn.close()
            return render_template("signup.html", error="Username already exists")

        hashed_password = generate_password_hash(password)

        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hashed_password)
        )
        conn.commit()
        conn.close()

        session["user"] = username
        return redirect(url_for("index"))

    return render_template("signup.html")


# Logout & User Account

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))


@app.route("/account")
def account():
    if not session.get("user"):
        return redirect(url_for("login"))

    conn = get_db_connection()

    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (session["user"],)
    ).fetchone()

    enrolled_courses = conn.execute("""
        SELECT courses.* FROM courses
        JOIN enrollments ON courses.id = enrollments.course_id
        WHERE enrollments.user_id = ?
    """, (user["id"],)).fetchall()

    conn.close()

    return render_template("account.html", user=session.get("user"), courses=enrolled_courses)


if __name__ == "__main__":
    app.run(debug=True)