# check_db.py
import sqlite3

DB_NAME = "library.db"

def show_table_info(table_name):
    print(f"\n=== {table_name} columns ===")
    cur.execute(f"PRAGMA table_info({table_name})")
    for row in cur.fetchall():
        print(row)

if __name__ == "__main__":
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Saare tables check karne ke liye
    tables = ["books", "students", "issued_books", "borrow_requests"]

    for t in tables:
        show_table_info(t)

    conn.close()
