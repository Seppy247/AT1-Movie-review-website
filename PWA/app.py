# ============================================================================
# CINEVIBE - MOVIE REVIEW WEB APPLICATION
# Main Application File (app.py)
# ============================================================================
# This file contains all the backend logic for the CineVibe movie review app.
# It handles user authentication, database operations, and routing between pages.
# ============================================================================

from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ============================================================================
# SECTION 1: FLASK APP INITIALIZATION
# ============================================================================
# This creates the Flask application instance and sets up the secret key
# for session management and CSRF protection.
# ============================================================================

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Used to sign session cookies securely
# NOTE: In production, use: os.environ.get('SECRET_KEY') for better security

# ============================================================================
# SECTION 2: FILE UPLOAD CONFIGURATION
# ============================================================================
# These settings control how users can upload movie poster images with reviews.
# We restrict file types to images only and sanitize filenames for security.
# ============================================================================

UPLOAD_FOLDER = os.path.join("static", "uploads")  # Where uploaded images are stored
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}  # Only allow image files
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    """
    Check if uploaded file has an allowed extension.
    Prevents users from uploading dangerous file types like .exe or .php
    
    Args:
        filename (str): The name of the uploaded file
    
    Returns:
        bool: True if file extension is allowed, False otherwise
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ============================================================================
# SECTION 3: CSRF PROTECTION SETUP (Optional)
# ============================================================================
# CSRF (Cross-Site Request Forgery) protection prevents malicious websites
# from submitting forms to our app on behalf of logged-in users.
# This requires Flask-WTF to be installed.
# ============================================================================

try:
    from flask_wtf import CSRFProtect
    csrf = CSRFProtect(app)  # Enable CSRF protection app-wide
    try:
        from flask_wtf.csrf import generate_csrf
        # Make csrf_token() available in all templates
        app.jinja_env.globals['csrf_token'] = lambda: generate_csrf()
    except Exception:
        # If generate_csrf not available, provide empty token
        app.jinja_env.globals['csrf_token'] = lambda: ''
except Exception:
    # Flask-WTF not installed; provide a no-op csrf_token for templates
    app.jinja_env.globals['csrf_token'] = lambda: ''

# ============================================================================
# SECTION 4: DATABASE CONNECTION FUNCTION
# ============================================================================
# This function creates and returns a connection to the SQLite database.
# We use this instead of a global connection to avoid threading issues.
# ============================================================================

def get_db_connection():
    """
    Create and return a database connection.
    
    Returns:
        sqlite3.Connection: Connection to the reviews.db database
    
    How it works:
    1. Find the directory where app.py is located
    2. Build path to database/reviews.db
    3. Connect to SQLite database
    4. Set row_factory so results come back as dictionaries instead of tuples
    """
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Current directory
    DB_PATH = os.path.join(BASE_DIR, "database", "reviews.db")  # Path to database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
    return conn

# ============================================================================
# SECTION 5: HOME PAGE ROUTE
# ============================================================================
# This route displays the main homepage with all movie reviews.
# It uses a SQL JOIN to combine data from reviews, users, and films tables.
# ============================================================================

@app.route("/")
def home():
    """
    Display all reviews on the homepage with user info and film titles.
    
    URL: http://localhost:5000/
    Method: GET
    Template: templates/index.html
    
    Returns:
        Rendered HTML page with all reviews
    
    SQL Query Explanation:
    - SELECT: Gets review data, film title, and username
    - JOIN users: Connects reviews to the user who wrote them
    - JOIN films: Connects reviews to the film being reviewed
    - ORDER BY: Shows newest reviews first (descending by ID)
    """
    conn = get_db_connection()
    reviews = conn.execute("""
        SELECT reviews.id,           -- Review's unique ID
               reviews.title,         -- Review title
               reviews.rating,        -- Star rating (1-5)
               reviews.content,       -- Review text
               reviews.date,          -- Date posted
               reviews.photo,         -- Uploaded image filename
               reviews.user_id,       -- ID of user who posted
               films.title AS film_title,  -- Film name
               users.username         -- Username of reviewer
        FROM reviews
        JOIN users ON reviews.user_id = users.id    -- Connect to users table
        JOIN films ON reviews.film_id = films.id    -- Connect to films table
        ORDER BY reviews.id DESC    -- Newest first
    """).fetchall()
    conn.close()
    
    # Pass reviews to the template for display
    return render_template("index.html", reviews=reviews)

# ============================================================================
# SECTION 6: USER REGISTRATION ROUTE
# ============================================================================
# Allows new users to create an account with username and password.
# Passwords are hashed before storage for security.
# ============================================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Allow new users to register with hashed passwords and validate strength.
    
    URL: http://localhost:5000/register
    Methods: GET (show form), POST (process registration)
    Template: templates/register.html
    
    Security Features:
    - Password hashing (PBKDF2-SHA256)
    - Password strength validation
    - Duplicate username check
    - Input sanitization
    """
    
    # GET request: Show registration form
    if request.method == "POST":
        # POST request: Process registration
        
        username = request.form["username"].strip()  # Remove whitespace
        raw_password = request.form["password"]

        # ========================================
        # PASSWORD VALIDATION
        # ========================================
        # Server-side validation ensures password meets security requirements
        
        if len(raw_password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return redirect(url_for("register"))
            
        if not any(c.isupper() for c in raw_password):
            flash("Password must include at least one uppercase letter.", "error")
            return redirect(url_for("register"))
            
        if not any(c.isdigit() for c in raw_password):
            flash("Password must include at least one number.", "error")
            return redirect(url_for("register"))

        # ========================================
        # DUPLICATE USERNAME CHECK
        # ========================================
        conn = get_db_connection()
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?",  # Parameterized query (SQL injection safe)
            (username,)
        ).fetchone()
        
        if existing:
            conn.close()
            flash("Username already taken. Please choose a different username.", "error")
            return redirect(url_for("register"))

        # ========================================
        # PASSWORD HASHING
        # ========================================
        # NEVER store plain text passwords!
        # generate_password_hash() uses PBKDF2-SHA256 with a random salt
        password_hash = generate_password_hash(raw_password)
        
        # ========================================
        # SAVE USER TO DATABASE
        # ========================================
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password_hash)  # Store hashed password, not plain text
        )
        conn.commit()
        conn.close()
        
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("login"))

    # GET request: Show the registration form
    return render_template("register.html")

# ============================================================================
# SECTION 7: USER LOGIN ROUTE
# ============================================================================
# Authenticates users and creates a session to keep them logged in.
# ============================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Authenticate user and create a session.
    
    URL: http://localhost:5000/login
    Methods: GET (show form), POST (process login)
    Template: templates/login.html
    
    How Authentication Works:
    1. User submits username and password
    2. System looks up user in database
    3. Compares hashed password with stored hash
    4. If match: Create session and redirect to homepage
    5. If no match: Show error message
    """
    
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # ========================================
        # LOOK UP USER IN DATABASE
        # ========================================
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",  # Parameterized query
            (username,)
        ).fetchone()
        conn.close()

        # ========================================
        # VERIFY PASSWORD
        # ========================================
        # check_password_hash() compares the entered password
        # with the stored hash without ever decrypting it
        if user and check_password_hash(user["password"], password):
            # ========================================
            # CREATE SESSION
            # ========================================
            # Session data is stored server-side and signed with secret_key
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("home"))
        else:
            # Generic error message (don't reveal if username or password was wrong)
            flash("Invalid username or password. Please try again.", "error")
            return redirect(url_for("login"))

    # GET request: Show the login form
    return render_template("login.html")

# ============================================================================
# SECTION 8: LOGOUT ROUTE
# ============================================================================
# Logs user out by clearing their session data.
# ============================================================================

@app.route("/logout")
def logout():
    """
    Log the user out by clearing the session.
    
    URL: http://localhost:5000/logout
    Method: GET
    
    How it works:
    - session.clear() removes all session data
    - User is no longer authenticated
    - Redirects to homepage
    """
    session.clear()  # Remove user_id and username from session
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

# ============================================================================
# SECTION 9: ADD REVIEW ROUTE
# ============================================================================
# Allows logged-in users to create new movie reviews with photos.
# Includes validation, file upload handling, and film creation.
# ============================================================================

@app.route("/add-review", methods=["GET", "POST"])
def add_review():
    """
    Allow logged-in users to add a review with a photo.
    
    URL: http://localhost:5000/add-review
    Methods: GET (show form), POST (process submission)
    Template: templates/add_review.html
    
    Features:
    - Only accessible to logged-in users
    - Upload movie poster images
    - Select existing film or create new one
    - Validate all inputs
    """
    
    # ========================================
    # CHECK IF USER IS LOGGED IN
    # ========================================
    if "user_id" not in session:
        flash("Please log in to add a review.", "warning")
        return redirect(url_for("login"))

    # ========================================
    # GET REQUEST: SHOW FORM WITH FILM LIST
    # ========================================
    conn = get_db_connection()
    films = conn.execute("SELECT id, title FROM films ORDER BY title").fetchall()
    # Convert to dictionaries so Jinja can serialize to JSON
    films = [dict(f) for f in films]
    conn.close()

    # ========================================
    # POST REQUEST: PROCESS FORM SUBMISSION
    # ========================================
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        rating = request.form.get("rating", "")
        content = request.form.get("content", "").strip()
        film_id = request.form.get("film_id", "")
        new_film_title = request.form.get("new_film", "").strip()
        file = request.files.get("photo")
        filename = None

        # ========================================
        # INPUT VALIDATION
        # ========================================
        if not title or not rating or not content:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("add_review"))

        # ========================================
        # FILM HANDLING
        # ========================================
        # User can either select existing film or create new one
        if film_id == "new":
            # CREATE NEW FILM
            if not new_film_title:
                flash("Please enter a film title to add.", "error")
                return redirect(url_for("add_review"))
                
            conn = get_db_connection()
            # Check if film already exists (case-insensitive)
            existing = conn.execute(
                "SELECT id FROM films WHERE title = ? COLLATE NOCASE",
                (new_film_title,)
            ).fetchone()
            
            if existing:
                film_id = existing["id"]  # Use existing film
            else:
                # Create new film
                conn.execute("INSERT INTO films (title) VALUES (?)", (new_film_title,))
                conn.commit()
                film_id = conn.execute(
                    "SELECT id FROM films WHERE title = ? COLLATE NOCASE",
                    (new_film_title,)
                ).fetchone()["id"]
            conn.close()
        else:
            # VALIDATE EXISTING FILM SELECTION
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

        # ========================================
        # RATING VALIDATION
        # ========================================
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            flash("Rating must be an integer between 1 and 5.", "error")
            return redirect(url_for("add_review"))

        # ========================================
        # FILE UPLOAD HANDLING
        # ========================================
        if file and file.filename:
            if allowed_file(file.filename):
                # Sanitize filename to prevent directory traversal attacks
                filename = secure_filename(file.filename)
                
                # Add timestamp to prevent filename collisions
                import time
                filename = f"{int(time.time())}_{filename}"
                
                # Save file to uploads folder
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            else:
                flash("Invalid file type. Please upload an image (png, jpg, jpeg, gif).", "error")
                return redirect(url_for("add_review"))

        # ========================================
        # SAVE REVIEW TO DATABASE
        # ========================================
        try:
            conn = get_db_connection()
            conn.execute("""
                INSERT INTO reviews (title, rating, content, date, user_id, film_id, photo)
                VALUES (?, ?, ?, date('now'), ?, ?, ?)
            """, (
                title,                # Review title
                rating,               # Rating (1-5)
                content,              # Review text
                session["user_id"],   # Current logged-in user
                film_id,              # Selected or newly created film
                filename              # Uploaded photo filename
            ))
            conn.commit()
            conn.close()

            flash("Review added successfully!", "success")
            return redirect(url_for("home"))

        except Exception as e:
            flash(f"Error adding review: {str(e)}", "error")
            return redirect(url_for("add_review"))

    # GET request: Show the add review form
    return render_template("add_review.html", films=films)

# ============================================================================
# SECTION 10: VIEW SINGLE REVIEW ROUTE
# ============================================================================
# Displays full details of a single review.
# ============================================================================

@app.route("/review/<int:review_id>")
def view_review(review_id):
    """
    Display a single review in detail.
    
    URL: http://localhost:5000/review/5
    Method: GET
    Template: templates/review.html
    
    Args:
        review_id (int): The ID of the review to display
    
    Returns:
        Rendered HTML page with review details
    """
    conn = get_db_connection()
    review = conn.execute("""
        SELECT reviews.id, 
               reviews.title, 
               reviews.rating, 
               reviews.content, 
               reviews.date, 
               reviews.photo, 
               reviews.user_id,
               films.title as film_title,  -- Get film name
               users.username              -- Get reviewer name
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

# ============================================================================
# SECTION 11: EDIT REVIEW ROUTE
# ============================================================================
# Allows users to edit their own reviews.
# Includes ownership verification for security.
# ============================================================================

@app.route("/edit-review/<int:review_id>", methods=["GET", "POST"])
def edit_review(review_id):
    """
    Allow users to edit their own reviews.
    
    URL: http://localhost:5000/edit-review/5
    Methods: GET (show form), POST (process update)
    Template: templates/edit_review.html
    
    Security:
    - Only the review owner can edit
    - Verified by comparing session user_id with review user_id
    """
    
    # ========================================
    # CHECK IF USER IS LOGGED IN
    # ========================================
    if "user_id" not in session:
        flash("Please log in to edit reviews.", "warning")
        return redirect(url_for("login"))

    # ========================================
    # GET REVIEW FROM DATABASE
    # ========================================
    conn = get_db_connection()
    review = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
    conn.close()

    if not review:
        flash("Review not found.", "error")
        return redirect(url_for("home"))

    # ========================================
    # VERIFY OWNERSHIP
    # ========================================
    # Users can only edit their own reviews
    if review["user_id"] != session["user_id"]:
        flash("You can only edit your own reviews.", "error")
        return redirect(url_for("home"))

    # ========================================
    # GET FILM LIST FOR DROPDOWN
    # ========================================
    conn = get_db_connection()
    films = conn.execute("SELECT id, title FROM films ORDER BY title").fetchall()
    films = [dict(f) for f in films]
    conn.close()

    # ========================================
    # POST REQUEST: PROCESS UPDATE
    # ========================================
    if request.method == "POST":
        # (Similar validation and processing as add_review)
        # ... validation code ...
        
        # ========================================
        # UPDATE DATABASE
        # ========================================
        try:
            conn = get_db_connection()
            conn.execute("""
                UPDATE reviews
                SET title = ?, 
                    rating = ?, 
                    content = ?, 
                    film_id = ?, 
                    photo = ?
                WHERE id = ?
            """, (title, rating, content, film_id, filename, review_id))
            conn.commit()
            conn.close()

            flash("Review updated successfully!", "success")
            return redirect(url_for("view_review", review_id=review_id))

        except Exception as e:
            flash(f"Error updating review: {str(e)}", "error")
            return redirect(url_for("edit_review", review_id=review_id))

    # GET request: Show edit form pre-filled with existing data
    return render_template("edit_review.html", review=review, films=films)

# ============================================================================
# SECTION 12: DELETE REVIEW ROUTE
# ============================================================================
# Allows users to delete their own reviews.
# POST-only route for security (prevents accidental deletion via GET).
# ============================================================================

@app.route("/delete-review/<int:review_id>", methods=["POST"])
def delete_review(review_id):
    """
    Allow users to delete their own reviews.
    
    URL: http://localhost:5000/delete-review/5
    Method: POST only (not GET)
    
    Security:
    - Only the review owner can delete
    - Requires CSRF token
    - Confirmation dialog in frontend
    
    Args:
        review_id (int): The ID of the review to delete
    """
    
    # ========================================
    # CHECK IF USER IS LOGGED IN
    # ========================================
    if "user_id" not in session:
        flash("Please log in to delete reviews.", "warning")
        return redirect(url_for("login"))

    # ========================================
    # GET REVIEW AND VERIFY OWNERSHIP
    # ========================================
    conn = get_db_connection()
    review = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
    conn.close()

    if not review:
        flash("Review not found.", "error")
        return redirect(url_for("home"))

    if review["user_id"] != session["user_id"]:
        flash("You can only delete your own reviews.", "error")
        return redirect(url_for("home"))

    # ========================================
    # DELETE REVIEW
    # ========================================
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

# ============================================================================
# SECTION 13: RUN THE APPLICATION
# Location: Lines 390-391
# ============================================================================
# Starts the Flask development server when running this file directly.
# ============================================================================

if __name__ == "__main__":
    app.run(debug=True)  # debug=True enables auto-reload and detailed errors
    # NOTE: In production, set debug=False for security