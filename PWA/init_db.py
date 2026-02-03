import sqlite3
import os
from werkzeug.security import generate_password_hash

# -------------------------
# DATABASE SETUP
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "reviews.db")

# Create database directory if it doesn't exist
os.makedirs(DB_DIR, exist_ok=True)

print("🎬 Setting up CineVibe database...")

# -------------------------
# CONNECT TO DATABASE
# -------------------------
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# -------------------------
# CREATE TABLES
# -------------------------
print("📊 Creating tables...")

# Users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

# Films table
cursor.execute("""
CREATE TABLE IF NOT EXISTS films (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT UNIQUE NOT NULL
)
""")

# Reviews table
cursor.execute("""
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
    content TEXT NOT NULL,
    date TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    film_id INTEGER NOT NULL,
    photo TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (film_id) REFERENCES films(id) ON DELETE CASCADE
)
""")

# -------------------------
# SEED SAMPLE DATA
# -------------------------
print("🌱 Seeding sample data...")

# Sample users (password: "password123" for all)
users = [
    ("alice", "password123"),
    ("bob", "password123"),
    ("charlie", "password123")
]

for username, password in users:
    hashed_pw = generate_password_hash(password)
    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hashed_pw)
        )
    except sqlite3.IntegrityError:
        pass  # User already exists

# Sample films
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

for film in films:
    try:
        cursor.execute("INSERT INTO films (title) VALUES (?)", (film,))
    except sqlite3.IntegrityError:
        pass  # Film already exists

# Sample reviews
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

for review_data in sample_reviews:
    try:
        user = cursor.execute("SELECT id FROM users WHERE username = ?", (review_data["user"],)).fetchone()
        film = cursor.execute("SELECT id FROM films WHERE title = ?", (review_data["film"],)).fetchone()
        
        if user and film:
            cursor.execute("""
                INSERT INTO reviews (title, rating, content, date, user_id, film_id)
                VALUES (?, ?, ?, date('now'), ?, ?)
            """, (
                review_data["title"],
                review_data["rating"],
                review_data["content"],
                user[0],
                film[0]
            ))
    except sqlite3.IntegrityError:
        pass

# -------------------------
# COMMIT AND CLOSE
# -------------------------
conn.commit()
conn.close()

print("✅ Database setup complete!")
print(f"📍 Database location: {DB_PATH}")
print("\n🔑 Sample login credentials:")
print("   Username: alice | Password: password123")
print("   Username: bob   | Password: password123")
print("   Username: charlie | Password: password123")