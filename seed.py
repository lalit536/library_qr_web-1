import sqlite3

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

def seed_data():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Agar table nahi hai to banayega
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT UNIQUE,
            available INTEGER DEFAULT 1
        )
    """)

    # Sample books insert karega
    cursor.executemany("""
        INSERT OR IGNORE INTO books (title, author, isbn, available)
        VALUES (?, ?, ?, ?)
    """, books)

    conn.commit()
    conn.close()
    print("✅ Sample books insert ho gayi hain!")

if __name__ == "__main__":
    seed_data()
