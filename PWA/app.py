from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps

# -----------------------
# CREATE FLASK APP
# -----------------------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-key")  # set FLASK_SECRET_KEY in env for production

# -----------------------
# FILE UPLOAD SETTINGS
# -----------------------
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB max upload
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    """Check if uploaded file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Make sure upload folder exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Optional: CSRF protection if flask-wtf is installed
try:
    from flask_wtf import CSRFProtect
    csrf = CSRFProtect(app)
    try:
        from flask_wtf.csrf import generate_csrf
        app.jinja_env.globals['csrf_token'] = lambda: generate_csrf()
    except Exception:
        app.jinja_env.globals['csrf_token'] = lambda: ''
except Exception:
    # flask-wtf not installed, consider `pip install flask-wtf` for CSRF protection
    app.jinja_env.globals['csrf_token'] = lambda: ''

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
            SELECT reviews.id,
                   reviews.title,
                   reviews.rating,
                   reviews.content,
                   reviews.date,
                   reviews.photo,
                   users.username,
                   films.title AS film_title
            FROM reviews
            JOIN users ON reviews.user_id = users.id
            JOIN films ON reviews.film_id = films.id
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
    conn = get_db_connection()
    films = conn.execute("SELECT id, title FROM films ORDER BY title").fetchall()
    conn.close()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        rating = request.form.get("rating", "")
        content = request.form.get("content", "").strip()
        film_id = request.form.get("film_id", "")
        file = request.files.get("photo")

        # Validation
        if not title or not rating or not content or not film_id:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("add_review"))

        # Validate rating
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            flash("Rating must be an integer between 1 and 5.", "error")
            return redirect(url_for("add_review"))

        # Validate film_id
        try:
            film_id = int(film_id)
        except ValueError:
            flash("Invalid film selection.", "error")
            return redirect(url_for("add_review"))

        # Verify film exists
        conn = get_db_connection()
        film = conn.execute("SELECT id FROM films WHERE id = ?", (film_id,)).fetchone()
        conn.close()
        if not film:
            flash("Selected film not found.", "error")
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
# Review helpers & CRUD
# -----------------------

def get_review(review_id):
    conn = get_db_connection()
    review = conn.execute("""
        SELECT reviews.*, users.username, films.title AS film_title
        FROM reviews
        JOIN users ON reviews.user_id = users.id
        JOIN films ON reviews.film_id = films.id
        WHERE reviews.id = ?
    """, (review_id,)).fetchone()
    conn.close()
    return review


@app.route("/review/<int:review_id>")
def view_review(review_id):
    review = get_review(review_id)
    if not review:
        abort(404)
    return render_template("review.html", review=review)


@app.route("/review/<int:review_id>/edit", methods=["GET", "POST"])
@login_required
def edit_review(review_id):
    review = get_review(review_id)
    if not review:
        abort(404)
    if review["user_id"] != session.get("user_id"):
        flash("You do not have permission to edit this review.", "error")
        return redirect(url_for("home"))

    conn = get_db_connection()
    films = conn.execute("SELECT id, title FROM films ORDER BY title").fetchall()
    conn.close()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        rating = request.form.get("rating", "")
        content = request.form.get("content", "").strip()
        film_id = request.form.get("film_id", "")
        file = request.files.get("photo")

        if not title or not rating or not content or not film_id:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("edit_review", review_id=review_id))

        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            flash("Rating must be an integer between 1 and 5.", "error")
            return redirect(url_for("edit_review", review_id=review_id))

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

        filename = review["photo"]
        # Handle new file upload
        if file and file.filename:
            if allowed_file(file.filename):
                new_filename = secure_filename(file.filename)
                import time
                new_filename = f"{int(time.time())}_{new_filename}"
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], new_filename))
                # remove old file if exists
                if filename:
                    old_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    try:
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    except Exception:
                        pass
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


@app.route("/review/<int:review_id>/delete", methods=["POST"])
@login_required
def delete_review(review_id):
    review = get_review(review_id)
    if not review:
        abort(404)
    if review["user_id"] != session.get("user_id"):
        flash("You do not have permission to delete this review.", "error")
        return redirect(url_for("home"))
    try:
        # delete photo file
        if review["photo"]:
            p = os.path.join(app.config["UPLOAD_FOLDER"], review["photo"])
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        conn = get_db_connection()
        conn.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
        conn.commit()
        conn.close()
        flash("Review deleted.", "success")
        return redirect(url_for("home"))
    except Exception as e:
        flash(f"Error deleting review: {str(e)}", "error")
        return redirect(url_for("home"))

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
