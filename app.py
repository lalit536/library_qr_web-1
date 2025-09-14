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
            # Case-sensitive check
            if username == "admin" and password == "admin123":
                session["role"] = "admin"
                session["username"] = "admin"
                flash("✅ Admin logged in successfully!", "success")
                return redirect(url_for("admin_dashboard"))
            else:
                flash("❌ Invalid Admin credentials!", "danger")

        # ---------- Student Login ----------
        elif role == "student":
            name = request.form.get("username", "").strip()
            library_code = request.form.get("library_code", "").strip()   # case-sensitive
            department = request.form.get("department", "").strip()

            if not name or not library_code or not department:
                flash("❌ All fields required!", "danger")
                return redirect(url_for("login"))

            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM students WHERE library_code=?", (library_code,))
            student = cur.fetchone()

            if student:
                # Case-sensitive student name check
                if student["name"] != name:
                    flash("❌ This Library Code belongs to another student!", "danger")
                    conn.close()
                    return redirect(url_for("login"))

                if not student["department"] and department:
                    cur.execute("UPDATE students SET department=? WHERE library_code=?",
                                (department, library_code))
                    conn.commit()
            else:
                # Insert new student with case-sensitive values
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
    cur.execute("""
        SELECT ib.id, ib.student_name, ib.library_code, ib.branch, b.title, ib.issue_date, ib.return_date, ib.actual_return
        FROM issued_books ib
        JOIN books b ON ib.book_id = b.id
        ORDER BY ib.issue_date DESC
    """)
    issued_books = cur.fetchall()
    conn.close()
    return render_template("admin_dashboard.html", books=books_list, issued_books=issued_books,
                           current_date=datetime.now().strftime("%Y-%m-%d"))

# ---------- Add Book ----------
@app.route("/add_book", methods=["GET", "POST"])
def add_book():
    if session.get("role") != "admin":
        flash("Unauthorized!", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        isbn = request.form.get("isbn", "").strip()
        if not title or not author or not isbn:
            flash("❌ All fields are required!", "danger")
            return redirect(url_for("add_book"))

        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO books (title, author, isbn, available) VALUES (?, ?, ?, ?)",
                        (title, author, isbn, 1))
            conn.commit()
            flash("✅ Book added successfully!", "success")
        except sqlite3.IntegrityError:
            flash("❌ ISBN already exists!", "danger")
        conn.close()
        return redirect(url_for("admin_dashboard"))

    return render_template("add_book.html")

# ---------- Issue Book (Admin) ----------
@app.route("/issue_book", methods=["GET", "POST"])
def issue_book():
    if session.get("role") != "admin":
        flash("Unauthorized!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    if request.method == "POST":
        student_name = request.form.get("student_name", "").strip()
        library_code = request.form.get("library_code", "").strip()   # case-sensitive
        branch = request.form.get("branch", "").strip()
        book_id = request.form.get("book_id")
        if not student_name or not library_code or not book_id:
            flash("❌ All fields are required!", "danger")
            conn.close()
            return redirect(url_for("issue_book"))

        cur.execute("SELECT * FROM books WHERE id=? AND available=1", (book_id,))
        book = cur.fetchone()
        if not book:
            flash("❌ Book not available!", "danger")
            conn.close()
            return redirect(url_for("issue_book"))

        issue_date = datetime.now()
        return_date = issue_date + timedelta(days=14)
        cur.execute("""INSERT INTO issued_books 
                       (student_name, library_code, branch, book_id, issue_date, return_date) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (student_name, library_code, branch, book_id,
                     issue_date.strftime("%Y-%m-%d"), return_date.strftime("%Y-%m-%d")))
        cur.execute("UPDATE books SET available=0 WHERE id=?", (book_id,))
        conn.commit()
        conn.close()
        flash(f"✅ Book issued to {student_name}!", "success")
        return redirect(url_for("admin_dashboard"))

    cur.execute("SELECT * FROM books WHERE available=1")
    available_books = cur.fetchall()
    conn.close()
    return render_template("issue_book.html", books=available_books)

# ---------- Delete Book (Admin) ----------
@app.route("/delete_book/<int:book_id>", methods=["POST"])
def delete_book(book_id):
    if session.get("role") != "admin":
        flash("Unauthorized!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM books WHERE id=?", (book_id,))
    book = cur.fetchone()
    if not book:
        flash("❌ Book not found!", "danger")
    else:
        cur.execute("DELETE FROM books WHERE id=?", (book_id,))
        conn.commit()
        flash(f"✅ Book '{book['title']}' deleted!", "success")
    conn.close()
    return redirect(url_for("admin_dashboard"))

# ---------- Admin Return Book ----------
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

    cur.execute("UPDATE issued_books SET actual_return=? WHERE id=?", (datetime.now().strftime("%Y-%m-%d"), issue_id))
    cur.execute("UPDATE books SET available=1 WHERE id=?", (issued_book["book_id"],))
    conn.commit()
    conn.close()
    flash("✅ Book returned!", "success")
    return redirect(url_for("admin_dashboard"))

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
        WHERE ib.student_name=? AND ib.library_code=?
        ORDER BY ib.issue_date DESC
    """, (name, library_code))
    issued_books_raw = cur.fetchall()
    issued_books = []
    for row in issued_books_raw:
        book = dict(row)
        if book.get("return_date"):
            try:
                book["return_date_obj"] = datetime.strptime(book["return_date"], "%Y-%m-%d").date()
            except:
                book["return_date_obj"] = None
        else:
            book["return_date_obj"] = None
        issued_books.append(book)

    cur.execute("SELECT * FROM students WHERE name=? AND library_code=?", (name, library_code))
    student = cur.fetchone()
    conn.close()
    return render_template(
        "student_dashboard.html",
        student=student,
        issued_books=issued_books,
        current_date=datetime.now().strftime("%Y-%m-%d"),
        current_date_obj=datetime.now().date()
    )

# ---------- Search Books ----------
@app.route("/search_books")
def search_books():
    if session.get("role") != "student":
        flash("Unauthorized!", "danger")
        return redirect(url_for("login"))

    library_code = session.get("library_code")
    if not library_code:
        flash("❌ Session expired!", "danger")
        return redirect(url_for("login"))

    query = request.args.get("q", "").strip()
    conn = get_db()
    cur = conn.cursor()
    if query:
        cur.execute("""SELECT * FROM books 
                       WHERE (title LIKE ? OR author LIKE ? OR isbn LIKE ?)""",
                    (f"%{query}%", f"%{query}%", f"%{query}%"))
        results = cur.fetchall()
    else:
        results = []
    conn.close()
    student = {
        "name": session.get("student_name"),
        "department": session.get("branch"),
        "library_code": library_code
    }
    return render_template("search_results.html", results=results, query=query, student=student)

# ---------- Borrow Book ----------
@app.route("/borrow_book/<int:book_id>")
def borrow_book(book_id):
    if session.get("role") != "student":
        flash("Unauthorized!", "danger")
        return redirect(url_for("login"))

    library_code = session.get("library_code")
    if not library_code:
        flash("❌ Session expired!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM books WHERE id=? AND available=1", (book_id,))
    book = cur.fetchone()
    if not book:
        flash("❌ Book not available!", "danger")
        conn.close()
        return redirect(url_for("student_dashboard", name=session.get("student_name")))

    issue_date = datetime.now()
    return_date = issue_date + timedelta(days=14)
    cur.execute("""INSERT INTO issued_books (student_name, library_code, branch, book_id, issue_date, return_date)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session.get("student_name"), library_code, session.get("branch"),
                 book_id, issue_date.strftime("%Y-%m-%d"), return_date.strftime("%Y-%m-%d")))
    cur.execute("UPDATE books SET available=0 WHERE id=?", (book_id,))
    conn.commit()
    conn.close()
    flash(f"📚 Book '{book['title']}' issued!", "success")
    return redirect(url_for("student_dashboard", name=session.get("student_name")))

# ---------- Return Book (Student) ----------
@app.route("/return_book/<int:issue_id>")
def return_book(issue_id):
    if session.get("role") != "student":
        flash("Unauthorized!", "danger")
        return redirect(url_for("login"))

    library_code = session.get("library_code")
    if not library_code:
        flash("❌ Session expired!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM issued_books WHERE id=?", (issue_id,))
    issued_book = cur.fetchone()
    if not issued_book:
        flash("❌ Record not found!", "danger")
        conn.close()
        return redirect(url_for("student_dashboard", name=session.get("student_name")))

    cur.execute("UPDATE issued_books SET actual_return=? WHERE id=?", (datetime.now().strftime("%Y-%m-%d"), issue_id))
    cur.execute("UPDATE books SET available=1 WHERE id=?", (issued_book["book_id"],))
    conn.commit()
    conn.close()
    flash("✅ Book returned!", "success")
    return redirect(url_for("student_dashboard", name=session.get("student_name")))

# ---------- Start Server ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
