import sqlite3
import hashlib

# Database ka naam
DB_NAME = "library.db"

# Sample books
books = [
    ("Python Programming", "John Doe", "9781234567890", 1),
    ("Data Science Basics", "Jane Smith", "9789876543210", 1),
    ("Machine Learning Guide", "Michael Lee", "9784567890123", 1),
    ("Deep Learning Essentials", "Anna Brown", "9781111111111", 1),
    ("Flask Web Development", "David Green", "9782222222222", 1),
]

# Sample colleges (password ko hash karke store karenge)
colleges = [
    ("ABC Engineering College", "ABC123", hashlib.sha256("password123".encode()).hexdigest()),
    ("XYZ Institute of Tech", "XYZ789", hashlib.sha256("admin123".encode()).hexdigest()),
]

def seed_data():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # ✅ Books table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT UNIQUE,
            available INTEGER DEFAULT 1
        )
    """)

    # ✅ Colleges table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS colleges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            college_code TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Sample books insert karega
    cursor.executemany("""
        INSERT OR IGNORE INTO books (title, author, isbn, available)
        VALUES (?, ?, ?, ?)
    """, books)

    # Sample colleges insert karega
    cursor.executemany("""
        INSERT OR IGNORE INTO colleges (name, college_code, password_hash)
        VALUES (?, ?, ?)
    """, colleges)

    conn.commit()
    conn.close()
    print("✅ Sample books & colleges insert ho gaye!")

if __name__ == "__main__":
    seed_data()
