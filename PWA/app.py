from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# -----------------------
# CREATE FLASK APP
# -----------------------
app = Flask(__name__)
# Prefer an environment-provided secret in production
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")  # Required for sessions

# -----------------------
# FILE UPLOAD SETTINGS
# -----------------------
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit

# Session cookie hardening (secure in production)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") == "production"

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Make sure upload folder exists (use absolute path inside app static)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Optional: CSRF helper for templates (works if Flask-WTF is installed)
try:
    from flask_wtf import CSRFProtect
    csrf = CSRFProtect(app)
    try:
        from flask_wtf.csrf import generate_csrf
        app.jinja_env.globals['csrf_token'] = lambda: generate_csrf()
    except Exception:
        app.jinja_env.globals['csrf_token'] = lambda: ''
except Exception:
    app.jinja_env.globals['csrf_token'] = lambda: ''

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
        SELECT reviews.id,
               reviews.title,
               reviews.rating,
               reviews.content,
               reviews.date,
               reviews.photo,
               reviews.user_id,
               films.title AS film_title,
               users.username
        FROM reviews
        JOIN users ON reviews.user_id = users.id
        JOIN films ON reviews.film_id = films.id
        ORDER BY reviews.id DESC
    """).fetchall()
    conn.close()
    return render_template("index.html", reviews=reviews)

# -----------------------
# REGISTER PAGE
# -----------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    """Allow new users to register with hashed passwords and validate strength."""
    if request.method == "POST":
        username = request.form["username"].strip()
        raw_password = request.form["password"]

        # Server-side password validation
        if len(raw_password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return redirect(url_for("register"))
        if not any(c.isupper() for c in raw_password):
            flash("Password must include at least one uppercase letter.", "error")
            return redirect(url_for("register"))
        if not any(c.isdigit() for c in raw_password):
            flash("Password must include at least one number.", "error")
            return redirect(url_for("register"))

        conn = get_db_connection()
        # Check if username already exists
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            conn.close()
            flash("Username already taken. Please choose a different username.", "error")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(raw_password)
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password_hash)
        )
        conn.commit()
        conn.close()
        flash("Account created successfully! Please log in.", "success")
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
            flash("Invalid username or password. Please try again.", "error")
            return redirect(url_for("login"))

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

    conn = get_db_connection()
    films = conn.execute("SELECT id, title FROM films ORDER BY title").fetchall()
    # convert sqlite3.Row objects to plain dicts so Jinja's tojson can serialize them
    films = [dict(f) for f in films]
    conn.close()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        rating = request.form.get("rating", "")
        content = request.form.get("content", "").strip()
        film_id = request.form.get("film_id", "")
        new_film_title = request.form.get("new_film", "").strip()
        file = request.files.get("photo")
        filename = None

        # Basic validation
        if not title or not rating or not content:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("add_review"))

        # Handle new film creation or validate existing film selection
        if film_id == "new":
            if not new_film_title:
                flash("Please enter a film title to add.", "error")
                return redirect(url_for("add_review"))
            conn = get_db_connection()
            existing = conn.execute("SELECT id FROM films WHERE title = ? COLLATE NOCASE", (new_film_title,)).fetchone()
            if existing:
                film_id = existing["id"]
            else:
                conn.execute("INSERT INTO films (title) VALUES (?)", (new_film_title,))
                conn.commit()
                film_id = conn.execute("SELECT id FROM films WHERE title = ? COLLATE NOCASE", (new_film_title,)).fetchone()["id"]
            conn.close()
        else:
            try:
                film_id = int(film_id)
            except ValueError:
                flash("Invalid film selection.", "error")
                return redirect(url_for("add_review"))
            conn = get_db_connection()
            film = conn.execute("SELECT id FROM films WHERE id = ?", (film_id,)).fetchone()
            conn.close()
            if not film:
                flash("Selected film not found.", "error")
                return redirect(url_for("add_review"))

        # Validate rating
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            flash("Rating must be an integer between 1 and 5.", "error")
            return redirect(url_for("add_review"))

        # Handle file upload
        if file and file.filename:
            if allowed_file(file.filename):
                orig_name = secure_filename(file.filename)
                ext = orig_name.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(save_path)
            else:
                flash("Invalid file type. Please upload an image (png, jpg, jpeg, gif).", "error")
                return redirect(url_for("add_review"))

        try:
            conn = get_db_connection()
            conn.execute("""
                INSERT INTO reviews (title, rating, content, date, user_id, film_id, photo)
                VALUES (?, ?, ?, date('now'), ?, ?, ?)
            """, (title, rating, content, session["user_id"], film_id, filename))
            conn.commit()
            conn.close()

            flash("Review added successfully!", "success")
            return redirect(url_for("home"))

        except Exception as e:
            flash(f"Error adding review: {str(e)}", "error")
            return redirect(url_for("add_review"))

    return render_template("add_review.html", films=films)

# -----------------------
# VIEW REVIEW PAGE
# -----------------------
@app.route("/review/<int:review_id>")
def view_review(review_id):
    """Display a single review."""
    conn = get_db_connection()
    review = conn.execute("""
        SELECT reviews.id, 
               reviews.title, 
               reviews.rating, 
               reviews.content, 
               reviews.date, 
               reviews.photo, 
               reviews.user_id,
               films.title as film_title,
               users.username
        FROM reviews
        JOIN films ON reviews.film_id = films.id
        JOIN users ON reviews.user_id = users.id
        WHERE reviews.id = ?
    """, (review_id,)).fetchone()
    conn.close()

    if not review:
        flash("Review not found.", "error")
        return redirect(url_for("home"))

    return render_template("review.html", review=review)

# -----------------------
# EDIT REVIEW PAGE
# -----------------------
@app.route("/edit-review/<int:review_id>", methods=["GET", "POST"])
def edit_review(review_id):
    """Allow users to edit their own reviews."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    review = conn.execute("""
        SELECT * FROM reviews WHERE id = ?
    """, (review_id,)).fetchone()
    conn.close()

    if not review:
        flash("Review not found.", "error")
        return redirect(url_for("home"))

    if review["user_id"] != session["user_id"]:
        flash("You can only edit your own reviews.", "error")
        return redirect(url_for("home"))

    conn = get_db_connection()
    films = conn.execute("SELECT id, title FROM films ORDER BY title").fetchall()
    films = [dict(f) for f in films]
    conn.close()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        rating = request.form.get("rating", "")
        content = request.form.get("content", "").strip()
        film_id = request.form.get("film_id", "")
        new_film_title = request.form.get("new_film", "").strip()
        file = request.files.get("photo")

        # Basic validation
        if not title or not rating or not content:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("edit_review", review_id=review_id))

        # Handle new film creation or validate existing film selection
        if film_id == "new":
            if not new_film_title:
                flash("Please enter a film title to add.", "error")
                return redirect(url_for("edit_review", review_id=review_id))
            conn = get_db_connection()
            existing = conn.execute("SELECT id FROM films WHERE title = ? COLLATE NOCASE", (new_film_title,)).fetchone()
            if existing:
                film_id = existing["id"]
            else:
                conn.execute("INSERT INTO films (title) VALUES (?)", (new_film_title,))
                conn.commit()
                film_id = conn.execute("SELECT id FROM films WHERE title = ? COLLATE NOCASE", (new_film_title,)).fetchone()["id"]
            conn.close()
        else:
            try:
                film_id = int(film_id)
            except ValueError:
                flash("Invalid film selection.", "error")
                return redirect(url_for("edit_review", review_id=review_id))
            conn = get_db_connection()
            film = conn.execute("SELECT id FROM films WHERE id = ?", (film_id,)).fetchone()
            conn.close()
            if not film:
                flash("Selected film not found.", "error")
                return redirect(url_for("edit_review", review_id=review_id))

        # Validate rating
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            flash("Rating must be an integer between 1 and 5.", "error")
            return redirect(url_for("edit_review", review_id=review_id))

        # Handle file upload
        filename = review["photo"]
        if file and file.filename:
            if allowed_file(file.filename):
                orig_name = secure_filename(file.filename)
                ext = orig_name.rsplit('.', 1)[1].lower()
                new_filename = f"{uuid.uuid4().hex}.{ext}"
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], new_filename)
                # delete old file if present
                old = review.get("photo")
                if old:
                    old_path = os.path.join(app.config["UPLOAD_FOLDER"], old)
                    try:
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    except Exception:
                        pass
                file.save(save_path)
                filename = new_filename
            else:
                flash("Invalid file type. Please upload an image (png, jpg, jpeg, gif).", "error")
                return redirect(url_for("edit_review", review_id=review_id))

        try:
            conn = get_db_connection()
            conn.execute("""
                UPDATE reviews
                SET title = ?, rating = ?, content = ?, film_id = ?, photo = ?
                WHERE id = ?
            """, (title, rating, content, film_id, filename, review_id))
            conn.commit()
            conn.close()

            flash("Review updated successfully!", "success")
            return redirect(url_for("view_review", review_id=review_id))

        except Exception as e:
            flash(f"Error updating review: {str(e)}", "error")
            return redirect(url_for("edit_review", review_id=review_id))

    return render_template("edit_review.html", review=review, films=films)

# -----------------------
# DELETE REVIEW PAGE
# -----------------------
@app.route("/delete-review/<int:review_id>", methods=["POST"])
def delete_review(review_id):
    """Allow users to delete their own reviews."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    review = conn.execute("""
        SELECT * FROM reviews WHERE id = ?
    """, (review_id,)).fetchone()
    conn.close()

    if not review:
        flash("Review not found.", "error")
        return redirect(url_for("home"))

    if review["user_id"] != session["user_id"]:
        flash("You can only delete your own reviews.", "error")
        return redirect(url_for("home"))

    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
        conn.commit()
        conn.close()

        flash("Review deleted successfully!", "success")
        return redirect(url_for("home"))

    except Exception as e:
        flash(f"Error deleting review: {str(e)}", "error")
        return redirect(url_for("home"))

# -----------------------
# RUN APP
# -----------------------
if __name__ == "__main__":
    app.run(debug=True)
