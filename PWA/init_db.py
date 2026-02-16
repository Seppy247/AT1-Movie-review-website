# ============================================================================
# CINEVIBE - DATABASE INITIALIZATION SCRIPT
# File: create_db.py
# ============================================================================
# This script creates the SQLite database and populates it with sample data.
# Run this file ONCE before starting the application for the first time.
# ============================================================================

import sqlite3
import os
from werkzeug.security import generate_password_hash

# ============================================================================
# SECTION 1: DATABASE PATH SETUP
# ============================================================================
# Determines where the database file will be created.
# Creates a 'database' folder if it doesn't already exist.
# ============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Directory where this script is
DB_DIR = os.path.join(BASE_DIR, "database")            # Create 'database' subdirectory
DB_PATH = os.path.join(DB_DIR, "reviews.db")           # Full path to reviews.db file

# Create the database directory if it doesn't exist
os.makedirs(DB_DIR, exist_ok=True)

print("Setting up CineVibe database...")

# ============================================================================
# SECTION 2: CONNECT TO DATABASE
# ============================================================================
# Creates or opens the SQLite database file.
# If the file doesn't exist, SQLite creates it automatically.
# ============================================================================

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ============================================================================
# SECTION 3: CREATE USERS TABLE
# ============================================================================
# Stores user account information.
# Passwords are NEVER stored in plain text - only hashed versions.
# ============================================================================

print("Creating tables...")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Unique ID for each user (auto-generated)
    username TEXT UNIQUE NOT NULL,         -- Username must be unique and cannot be empty
    password TEXT NOT NULL                 -- Hashed password (NOT plain text)
)
""")

# - id: Unique identifier for each user, auto-increments (1, 2, 3...)
# - username: How users log in, must be unique (no duplicates)
# - password: Stored as hash (e.g., pbkdf2:sha256:600000$...)
# - UNIQUE constraint: Prevents two users with same username
# - NOT NULL constraint: These fields must have a value

# ============================================================================
# SECTION 4: CREATE FILMS TABLE
# ============================================================================
# Stores movie/film titles.
# Separate table allows multiple reviews of the same film without duplication.
# ============================================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS films (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Unique ID for each film
    title TEXT UNIQUE NOT NULL             -- Film title (e.g., "The Matrix")
)
""")

# WHY A SEPARATE FILMS TABLE?
# Instead of storing film title in every review (duplication), we:
# 1. Store each film ONCE in the films table
# 2. Link reviews to films using film_id (foreign key)
# 
# Benefits:
# - No duplicate film names
# - Easy to find all reviews for a specific film
# - If we want to add film data (year, director), it's in one place

# ============================================================================
# SECTION 5: CREATE REVIEWS TABLE
# ============================================================================
# Stores movie reviews written by users.
# Links to both users table (who wrote it) and films table (what film).
# ============================================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,                          -- Unique review ID
    title TEXT NOT NULL,                                           -- Review title/headline
    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),   -- Star rating (1-5 only)
    content TEXT NOT NULL,                                         -- The actual review text
    date TEXT NOT NULL,                                            -- When review was posted
    user_id INTEGER NOT NULL,                                      -- Who wrote this review
    film_id INTEGER NOT NULL,                                      -- Which film was reviewed
    photo TEXT,                                                    -- Filename of uploaded image (optional)
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,  -- Link to users table
    FOREIGN KEY (film_id) REFERENCES films(id) ON DELETE CASCADE   -- Link to films table
)
""")

# FIELD EXPLANATIONS:
# 
# - id: Unique identifier for each review
# - title: Short headline (e.g., "Amazing sci-fi masterpiece!")
# - rating: Star rating between 1-5 (enforced by CHECK constraint)
# - content: Full review text
# - date: Date review was posted (format: YYYY-MM-DD)
# - user_id: References users.id (who wrote the review)
# - film_id: References films.id (which film was reviewed)
# - photo: Filename of uploaded poster image (optional, can be NULL)
#
# FOREIGN KEYS:
# - user_id links to users.id
# - film_id links to films.id
# - ON DELETE CASCADE: If a user is deleted, their reviews are also deleted
#   (prevents orphaned reviews with no author)
#
# CHECK CONSTRAINT:
# - rating >= 1 AND rating <= 5 ensures rating is always 1, 2, 3, 4, or 5
# - Database rejects any rating outside this range

# ============================================================================
# SECTION 6: SEED SAMPLE USERS
# ============================================================================
# Creates test user accounts so you can log in immediately.
# Passwords are hashed before storage (security best practice).
# ============================================================================

print("Seeding sample data...")

# Sample users with plain text passwords (will be hashed below)
users = [
    ("alice", "password123"),
    ("bob", "password123"),
    ("charlie", "password123")
]

# Insert each user into the database
for username, password in users:
    # Hash the password using PBKDF2-SHA256 with random salt
    hashed_pw = generate_password_hash(password)
    
    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hashed_pw)  # Store username and HASHED password
        )
    except sqlite3.IntegrityError:
        # User already exists (UNIQUE constraint violation)
        pass  # Skip if user already in database


# ============================================================================
# SECTION 7: SEED SAMPLE FILMS
# ============================================================================
# Populates the films table with popular movies.
# Users can add more films when creating reviews.
# ============================================================================

films = [
    "The Matrix",
    "Inception",
    "Interstellar",
    "The Shawshank Redemption",
    "Pulp Fiction",
    "The Dark Knight",
    "Forrest Gump",
    "Fight Club",
    "The Godfather",
    "Goodfellas"
]

# Insert each film into the database
for film in films:
    try:
        cursor.execute("INSERT INTO films (title) VALUES (?)", (film,))
    except sqlite3.IntegrityError:
        # Film already exists (UNIQUE constraint on title)
        pass  # Skip if film already in database


# ============================================================================
# SECTION 8: SEED SAMPLE REVIEWS
# ============================================================================
# Creates example reviews so the homepage isn't empty on first run.
# Shows how the JOIN queries work to connect reviews, users, and films.
# ============================================================================

sample_reviews = [
    {
        "title": "Mind-bending masterpiece",
        "rating": 5,
        "content": "The Matrix redefined sci-fi cinema. The action sequences are groundbreaking and the philosophical themes are thought-provoking. A must-watch for any film enthusiast.",
        "user": "alice",
        "film": "The Matrix"
    },
    {
        "title": "Nolan's best work",
        "rating": 5,
        "content": "Inception is a visually stunning journey through dreams within dreams. The concept is brilliant and the execution is flawless. Hans Zimmer's score elevates every scene.",
        "user": "bob",
        "film": "Inception"
    },
    {
        "title": "Space epic done right",
        "rating": 4,
        "content": "Interstellar combines hard science with emotional storytelling. The visuals are breathtaking and the ending is both confusing and beautiful. Not perfect but definitely worth watching.",
        "user": "charlie",
        "film": "Interstellar"
    }
]

# Insert each sample review
for review_data in sample_reviews:
    try:
        # Look up user ID from username
        user = cursor.execute(
            "SELECT id FROM users WHERE username = ?",
            (review_data["user"],)
        ).fetchone()
        
        # Look up film ID from film title
        film = cursor.execute(
            "SELECT id FROM films WHERE title = ?",
            (review_data["film"],)
        ).fetchone()
        
        # Only insert if both user and film exist
        if user and film:
            cursor.execute("""
                INSERT INTO reviews (title, rating, content, date, user_id, film_id)
                VALUES (?, ?, ?, date('now'), ?, ?)
            """, (
                review_data["title"],    # Review title
                review_data["rating"],   # Star rating
                review_data["content"],  # Review text
                user[0],                 # user_id (from users table)
                film[0]                  # film_id (from films table)
            ))
    except sqlite3.IntegrityError:
        pass  # Skip if review already exists

conn.commit()  # Save all changes (tables and data)
conn.close()   # Close database connection

# ============================================================================
# SUCCESS MESSAGE
# ============================================================================

print("✅ Database setup complete!")
print(f"📍 Database location: {DB_PATH}")
print("\n🔑 Sample login credentials:")
print("   Username: alice   | Password: password123")
print("   Username: bob     | Password: password123")
print("   Username: charlie | Password: password123")