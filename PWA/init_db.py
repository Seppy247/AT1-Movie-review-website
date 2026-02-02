import sqlite3
import os
from werkzeug.security import generate_password_hash

# -------------------------
# DATABASE PATH (SAFE)
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "reviews.db")

# Make sure database folder exists
os.makedirs(DB_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# -------------------------
# USERS TABLE
# -------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

# -------------------------
# FILMS TABLE
# -------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS films (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL
)
""")

# -------------------------
# REVIEWS TABLE (added photo column)
# -------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    rating INTEGER NOT NULL,
    content TEXT NOT NULL,
    date TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    film_id INTEGER NOT NULL,
    photo TEXT,  -- new column for uploaded image filename
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (film_id) REFERENCES films(id)
)
""")

# -------------------------
# INSERT SAMPLE USERS (hashed passwords)
# -------------------------
users = [
    ("alice", "password1"),
    ("bob", "password2"),
    ("charlie", "password3")
]

for username, pw in users:
    hashed_pw = generate_password_hash(pw)
    cursor.execute(
        "INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)",
        (username, hashed_pw)
    )

# -------------------------
# INSERT SAMPLE FILMS
# -------------------------
films = [
    "The Matrix",
    "Inception",
    "Interstellar",
    "The Witcher 3",
    "Red Dead Redemption 2",
    "Cyberpunk 2077"
]

for film in films:
    cursor.execute("INSERT OR IGNORE INTO films (title) VALUES (?)", (film,))

# -------------------------
# SAVE AND CLOSE
# -------------------------
conn.commit()
conn.close()

print("Database created successfully.")
