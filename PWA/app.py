from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# -----------------------
# CREATE FLASK APP
# -----------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"  # Required for sessions

# -----------------------
# FILE UPLOAD SETTINGS
# -----------------------
UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Make sure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -----------------------
# DATABASE CONNECTION
# -----------------------
def get_db_connection():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "database", "reviews.db")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# -----------------------
# HOME PAGE
# -----------------------
@app.route("/")
def home():
    """Display all reviews on the homepage with user info."""
    conn = get_db_connection()
    reviews = conn.execute("""
        SELECT reviews.title,
               reviews.rating,
               reviews.content,
               reviews.date,
               reviews.photo,
               users.username
        FROM reviews
        JOIN users ON reviews.user_id = users.id
        ORDER BY reviews.id DESC
    """).fetchall()
    conn.close()
    return render_template("index.html", reviews=reviews)

# -----------------------
# REGISTER PAGE
# -----------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    """Allow new users to register with hashed passwords."""
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("login"))

    return render_template("register.html")

# -----------------------
# LOGIN PAGE
# -----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate user and create a session."""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("home"))
        else:
            return "Invalid login credentials. Please try again."

    return render_template("login.html")

# -----------------------
# LOGOUT PAGE
# -----------------------
@app.route("/logout")
def logout():
    """Log the user out by clearing the session."""
    session.clear()
    return redirect(url_for("home"))

# -----------------------
# ADD REVIEW PAGE
# -----------------------
@app.route("/add-review", methods=["GET", "POST"])
def add_review():
    """Allow logged-in users to add a review with a photo."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form["title"]
        rating = request.form["rating"]
        content = request.form["content"]
        file = request.files.get("photo")
        filename = None

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO reviews (title, rating, content, date, user_id, film_id, photo)
            VALUES (?, ?, ?, date('now'), ?, 1, ?)
        """, (title, rating, content, session["user_id"], filename))
        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    return render_template("add_review.html")

# -----------------------
# RUN APP
# -----------------------
if __name__ == "__main__":
    app.run(debug=True)
