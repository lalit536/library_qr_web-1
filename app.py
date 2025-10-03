# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "library-secret"

DB_NAME = "library.db"

# ---------- Database Setup ----------
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Books table
        cursor.execute("""CREATE TABLE IF NOT EXISTS books (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title TEXT NOT NULL,
                            author TEXT NOT NULL,
                            isbn TEXT UNIQUE NOT NULL,
                            available INTEGER DEFAULT 1
                        )""")

        # Issued books table
        cursor.execute("""CREATE TABLE IF NOT EXISTS issued_books (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            student_name TEXT NOT NULL,
                            library_code TEXT NOT NULL,
                            branch TEXT,
                            book_id INTEGER,
                            issue_date TEXT,
                            return_date TEXT,
                            actual_return TEXT
                        )""")

        # Students table
        cursor.execute("""CREATE TABLE IF NOT EXISTS students (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            library_code TEXT UNIQUE NOT NULL,
                            department TEXT,
                            approved INTEGER DEFAULT 1
                        )""")

        # Borrow Requests table
        cursor.execute("""CREATE TABLE IF NOT EXISTS borrow_requests (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            student_username TEXT NOT NULL,  -- actually stores library_code
                            book_id INTEGER,
                            request_date TEXT,
                            status TEXT DEFAULT 'pending'
                        )""")

        conn.commit()

# ---------- Helper ----------
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- Login ----------
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role")

        # ---------- Admin Login ----------
        if role == "admin":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            if username == "admin" and password == "88888888":
                session["role"] = "admin"
                session["username"] = "admin"
                flash("✅ Admin logged in successfully!", "success")
                return redirect(url_for("admin_dashboard"))
            else:
                flash("❌ Invalid Admin credentials!", "danger")

        # ---------- Student Login ----------
        elif role == "student":
            name = request.form.get("username", "").strip()
            library_code = request.form.get("library_code", "").strip()
            department = request.form.get("department", "").strip()

            if not name or not library_code or not department:
                flash("❌ All fields required!", "danger")
                return redirect(url_for("login"))

            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM students WHERE library_code=?", (library_code,))
            student = cur.fetchone()

            if student:
                if student["name"] != name:
                    flash("❌ This Library Code belongs to another student!", "danger")
                    conn.close()
                    return redirect(url_for("login"))

                if not student["department"] and department:
                    cur.execute("UPDATE students SET department=? WHERE library_code=?",
                                (department, library_code))
                    conn.commit()
            else:
                cur.execute("""INSERT INTO students (name, library_code, department, approved) 
                               VALUES (?, ?, ?, ?)""",
                            (name, library_code, department, 1))
                conn.commit()
                cur.execute("SELECT * FROM students WHERE library_code=?", (library_code,))
                student = cur.fetchone()

            session["role"] = "student"
            session["student_name"] = student["name"]
            session["branch"] = student["department"] if student["department"] else department
            session["library_code"] = student["library_code"]

            conn.close()
            flash(f"👋 Welcome {student['name']}!", "success")
            return redirect(url_for("student_dashboard", name=student["name"]))

    return render_template("login.html")

# ---------- Logout ----------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))

# ---------- Admin Dashboard ----------
@app.route("/admin_dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        flash("Only Admin can access this section!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM books")
    books_list = cur.fetchall()

    # Issued books
    cur.execute("""
        SELECT ib.id, ib.student_name, ib.library_code, ib.branch, 
               b.title, ib.issue_date, ib.return_date, ib.actual_return
        FROM issued_books ib
        JOIN books b ON ib.book_id = b.id
        ORDER BY ib.issue_date DESC
    """)
    issued_books = cur.fetchall()

    # ✅ Only pending Borrow Requests
    cur.execute("""
        SELECT br.id, s.name AS student_name, s.department AS branch, 
               b.title, br.status, br.request_date, s.library_code
        FROM borrow_requests br
        JOIN books b ON br.book_id = b.id
        JOIN students s ON br.student_username = s.library_code
        WHERE br.status = 'pending'
        ORDER BY br.request_date DESC
    """)
    borrow_requests = cur.fetchall()

    conn.close()
    return render_template("admin_dashboard.html",
                           books=books_list,
                           issued_books=issued_books,
                           borrow_requests=borrow_requests,
                           current_date=datetime.now().strftime("%Y-%m-%d"))

# ---------- Delete Book (Admin) ----------
@app.route("/delete_book/<int:book_id>", methods=["POST"])
def delete_book(book_id):
    if session.get("role") != "admin":
        flash("Unauthorized!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM issued_books WHERE book_id=? AND actual_return IS NULL", (book_id,))
    issued = cur.fetchone()
    if issued:
        flash("❌ Cannot delete! Book is currently issued.", "danger")
        conn.close()
        return redirect(url_for("admin_dashboard"))

    cur.execute("DELETE FROM books WHERE id=?", (book_id,))
    conn.commit()
    conn.close()

    flash("🗑️ Book deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))

# ---------- Approve Borrow Request ----------
@app.route("/approve_request/<int:request_id>", methods=["POST"])
def approve_request(request_id):
    if session.get("role") != "admin":
        flash("Unauthorized!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM borrow_requests WHERE id=?", (request_id,))
    req = cur.fetchone()

    if not req:
        flash("❌ Request not found!", "danger")
        conn.close()
        return redirect(url_for("admin_dashboard"))

    # Check if book available
    cur.execute("SELECT * FROM books WHERE id=? AND available=1", (req["book_id"],))
    book = cur.fetchone()
    if not book:
        flash("❌ Book not available!", "danger")
        conn.close()
        return redirect(url_for("admin_dashboard"))

    # Fetch student info
    cur.execute("SELECT * FROM students WHERE library_code=?", (req["student_username"],))
    student = cur.fetchone()
    if not student:
        flash("❌ Student not found!", "danger")
        conn.close()
        return redirect(url_for("admin_dashboard"))

    issue_date = datetime.now()
    return_date = issue_date + timedelta(days=14)

    cur.execute("""INSERT INTO issued_books (student_name, library_code, branch, book_id, issue_date, return_date)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (student["name"], student["library_code"], student["department"], req["book_id"],
                 issue_date.strftime("%Y-%m-%d"), return_date.strftime("%Y-%m-%d")))

    cur.execute("UPDATE books SET available=0 WHERE id=?", (req["book_id"],))
    cur.execute("UPDATE borrow_requests SET status='approved' WHERE id=?", (request_id,))
    conn.commit()
    conn.close()

    flash(f"✅ Book issued to {student['name']} ({student['library_code']})", "success")
    return redirect(url_for("admin_dashboard"))

# ---------- Reject Borrow Request ----------
@app.route("/reject_request/<int:request_id>", methods=["POST"])
def reject_request(request_id):
    if session.get("role") != "admin":
        flash("Unauthorized!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE borrow_requests SET status='rejected' WHERE id=?", (request_id,))
    conn.commit()
    conn.close()

    flash("❌ Request rejected!", "info")
    return redirect(url_for("admin_dashboard"))

# ---------- Mark Book Returned (Admin) ----------
@app.route("/admin_return/<int:issue_id>", methods=["POST"])
def admin_return(issue_id):
    if session.get("role") != "admin":
        flash("Unauthorized!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM issued_books WHERE id=?", (issue_id,))
    issued_book = cur.fetchone()
    if not issued_book:
        flash("❌ Record not found!", "danger")
        conn.close()
        return redirect(url_for("admin_dashboard"))

    cur.execute("UPDATE issued_books SET actual_return=? WHERE id=?",
                (datetime.now().strftime("%Y-%m-%d"), issue_id))
    cur.execute("UPDATE books SET available=1 WHERE id=?", (issued_book["book_id"],))
    conn.commit()
    conn.close()
    flash("✅ Book marked as returned!", "success")
    return redirect(url_for("admin_dashboard"))

# ---------- Borrow Book (Student makes request) ----------
@app.route("/borrow_book/<int:book_id>")
def borrow_book(book_id):
    if session.get("role") != "student":
        flash("Unauthorized!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    library_code = session.get("library_code")

    cur.execute("SELECT * FROM borrow_requests WHERE book_id=? AND student_username=?", 
                (book_id, library_code))
    existing = cur.fetchone()
    if existing:
        flash("⚠️ You already requested this book!", "warning")
        conn.close()
        return redirect(url_for("student_dashboard", name=session.get("student_name")))

    cur.execute("""INSERT INTO borrow_requests (student_username, book_id, request_date, status)
                   VALUES (?, ?, ?, 'pending')""",
                (library_code, book_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    flash("📩 Borrow request sent! Waiting for admin approval.", "info")
    return redirect(url_for("student_dashboard", name=session.get("student_name")))

# ---------- Student Dashboard ----------
@app.route("/student/<name>")
def student_dashboard(name):
    if session.get("role") != "student" or session.get("student_name") != name:
        flash("Unauthorized!", "danger")
        return redirect(url_for("login"))

    library_code = session.get("library_code")
    if not library_code:
        flash("❌ Session expired!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT ib.id, b.title, ib.issue_date, ib.return_date, ib.actual_return, b.id as book_id
        FROM issued_books ib
        JOIN books b ON ib.book_id = b.id
        WHERE ib.library_code=?
        ORDER BY ib.issue_date DESC
    """, (library_code,))
    issued_books = cur.fetchall()
    conn.close()

    return render_template("student_dashboard.html",
                           student={"name": session.get("student_name"),
                                    "department": session.get("branch"),
                                    "library_code": library_code},
                           issued_books=issued_books,
                           current_date=datetime.now().strftime("%Y-%m-%d"))

# ---------- Return Book (Student) ----------
@app.route("/return_book/<int:issue_id>")
def return_book(issue_id):
    if session.get("role") != "student":
        flash("Unauthorized!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM issued_books WHERE id=?", (issue_id,))
    issued_book = cur.fetchone()
    if not issued_book:
        flash("❌ Record not found!", "danger")
        conn.close()
        return redirect(url_for("student_dashboard", name=session.get("student_name")))

    cur.execute("UPDATE issued_books SET actual_return=? WHERE id=?",
                (datetime.now().strftime("%Y-%m-%d"), issue_id))
    cur.execute("UPDATE books SET available=1 WHERE id=?", (issued_book["book_id"],))
    conn.commit()
    conn.close()
    flash("✅ Book returned!", "success")
    return redirect(url_for("student_dashboard", name=session.get("student_name")))

# ---------- Search Books ----------
@app.route("/search_books", methods=["GET"])
def search_books():
    query = request.args.get("q", "").strip()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM books WHERE title LIKE ? OR author LIKE ?", 
                (f"%{query}%", f"%{query}%"))
    results = cur.fetchall()
    conn.close()
    return render_template("search_results.html", results=results, query=query)

# ---------- Start Server ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
