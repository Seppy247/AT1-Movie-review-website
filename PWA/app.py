from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps

# -----------------------
# CREATE FLASK APP
# -----------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"  # Change this to a random secret key in production

# -----------------------
# FILE UPLOAD SETTINGS
# -----------------------
UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    """Check if uploaded file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Make sure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -----------------------
# DATABASE CONNECTION
# -----------------------
def get_db_connection():
    """Create and return a database connection."""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "database", "reviews.db")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# -----------------------
# LOGIN REQUIRED DECORATOR
# -----------------------
def login_required(f):
    """Decorator to require login for certain routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# -----------------------
# HOME PAGE
# -----------------------
@app.route("/")
def home():
    """Display all reviews on the homepage with user info."""
    try:
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
    except Exception as e:
        flash(f"Error loading reviews: {str(e)}", "error")
        return render_template("index.html", reviews=[])

# -----------------------
# REGISTER PAGE
# -----------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    """Allow new users to register with hashed passwords."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Validation
        if not username or not password:
            flash("Username and password are required.", "error")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return redirect(url_for("register"))

        try:
            conn = get_db_connection()
            
            # Check if username already exists
            existing_user = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,)
            ).fetchone()

            if existing_user:
                flash("Username already exists. Please choose another.", "error")
                conn.close()
                return redirect(url_for("register"))

            # Create new user
            hashed_password = generate_password_hash(password)
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_password)
            )
            conn.commit()
            conn.close()

            flash("Account created successfully! Please login.", "success")
            return redirect(url_for("login"))

        except Exception as e:
            flash(f"Error creating account: {str(e)}", "error")
            return redirect(url_for("register"))

    return render_template("register.html")

# -----------------------
# LOGIN PAGE
# -----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate user and create a session."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Please enter both username and password.", "error")
            return redirect(url_for("login"))

        try:
            conn = get_db_connection()
            user = conn.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            ).fetchone()
            conn.close()

            if user and check_password_hash(user["password"], password):
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                flash(f"Welcome back, {user['username']}!", "success")
                return redirect(url_for("home"))
            else:
                flash("Invalid username or password. Please try again.", "error")
                return redirect(url_for("login"))

        except Exception as e:
            flash(f"Error during login: {str(e)}", "error")
            return redirect(url_for("login"))

    return render_template("login.html")

# -----------------------
# LOGOUT PAGE
# -----------------------
@app.route("/logout")
def logout():
    """Log the user out by clearing the session."""
    username = session.get("username", "User")
    session.clear()
    flash(f"Goodbye, {username}! You've been logged out.", "info")
    return redirect(url_for("home"))

# -----------------------
# ADD REVIEW PAGE
# -----------------------
@app.route("/add-review", methods=["GET", "POST"])
@login_required
def add_review():
    """Allow logged-in users to add a review with a photo."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        rating = request.form.get("rating", "")
        content = request.form.get("content", "").strip()
        file = request.files.get("photo")

        # Validation
        if not title or not rating or not content:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("add_review"))

        if not file:
            flash("Please upload a movie photo.", "error")
            return redirect(url_for("add_review"))

        filename = None

        # Handle file upload
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to filename to avoid collisions
            import time
            filename = f"{int(time.time())}_{filename}"
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        else:
            flash("Invalid file type. Please upload an image (png, jpg, jpeg, gif).", "error")
            return redirect(url_for("add_review"))

        try:
            conn = get_db_connection()
            conn.execute("""
                INSERT INTO reviews (title, rating, content, date, user_id, film_id, photo)
                VALUES (?, ?, ?, date('now'), ?, 1, ?)
            """, (title, rating, content, session["user_id"], filename))
            conn.commit()
            conn.close()

            flash("Review added successfully!", "success")
            return redirect(url_for("home"))

        except Exception as e:
            flash(f"Error adding review: {str(e)}", "error")
            return redirect(url_for("add_review"))

    return render_template("add_review.html")

# -----------------------
# ERROR HANDLERS
# -----------------------
@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    flash("Page not found.", "error")
    return redirect(url_for("home"))

@app.errorhandler(500)
def internal_server_error(e):
    """Handle 500 errors."""
    flash("Something went wrong. Please try again.", "error")
    return redirect(url_for("home"))

# -----------------------
# RUN APP
# -----------------------
if __name__ == "__main__":
    app.run(debug=True)
