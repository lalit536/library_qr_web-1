import cv2
import sqlite3
from datetime import datetime, timedelta

# --- Database setup ---
conn = sqlite3.connect("library.db")
cursor = conn.cursor()

# Table ensure
cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_title TEXT,
    student_name TEXT,
    issue_date TEXT,
    due_date TEXT,
    return_date TEXT
)
""")
conn.commit()

# --- QRCode detector ---
detector = cv2.QRCodeDetector()

# Apna QR code image ka path
img = cv2.imread("static/qrcodes/book_1.png")

# Detect and decode
data, bbox, _ = detector.detectAndDecode(img)

def issue_book(book_title, student_name):
    """Book issue karne ka function"""
    issue_date = datetime.today().strftime("%Y-%m-%d")
    due_date = (datetime.today() + timedelta(days=14)).strftime("%Y-%m-%d")

    cursor.execute("""
    INSERT INTO transactions (book_title, student_name, issue_date, due_date, return_date)
    VALUES (?, ?, ?, ?, NULL)
    """, (book_title, student_name, issue_date, due_date))
    conn.commit()
    print(f"✅ Book '{book_title}' issued to {student_name}. Due on {due_date}")

def return_book(student_name, book_title):
    """Book return karne ka function"""
    return_date = datetime.today().strftime("%Y-%m-%d")

    cursor.execute("""
    UPDATE transactions 
    SET return_date = ? 
    WHERE student_name = ? AND book_title = ? AND return_date IS NULL
    """, (return_date, student_name, book_title))
    conn.commit()

    if cursor.rowcount > 0:
        print(f"📚 Book '{book_title}' returned by {student_name} on {return_date}")
    else:
        print("⚠️ No active issue record found for this book/student.")

# --- Main logic ---
if data:
    print("📌 QR Content:", data)

    # Example: student ka naam manually dal rahe hain (later input() ya scanner se le sakte ho)
    student_name = "Rahul Sharma"

    # Issue book
    issue_book(data, student_name)

    # Example return (test karne ke liye, jab book return ho to call karo)
    # return_book(student_name, data)

else:
    print("❌ QR Code not detected")

# --- Close DB ---
conn.close()
s