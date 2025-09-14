import sqlite3

DB_NAME = "library.db"

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

# Borrow requests table create karna
cur.execute("""
CREATE TABLE IF NOT EXISTS borrow_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_username TEXT NOT NULL,
    book_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (book_id) REFERENCES books(id)
)
""")

conn.commit()
conn.close()

print("✅ borrow_requests table created successfully!")
