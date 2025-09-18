import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import openpyxl
from flask_babel import Babel, _

app = Flask(__name__)
app.secret_key = "your_secret_key"  # change this to a secure random key

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---- Flask-Babel Setup ----
app.config["BABEL_DEFAULT_LOCALE"] = "en"   # Default language
app.config["BABEL_TRANSLATION_DIRECTORIES"] = "translations"
babel = Babel(app)


def get_locale():
    # Check if user already picked a language
    if "lang" in session:
        return session["lang"]
    # Otherwise fallback
    return request.accept_languages.best_match(["en", "pl"])

babel = Babel(app, locale_selector=get_locale)


# ---- Language Switcher ----
@app.route('/set_language/<lang>')
def set_language(lang):
    session["lang"] = lang
    return redirect(request.referrer or url_for('home'))

# ---- Initialize Database ----
def init_db():
    conn = sqlite3.connect("codes.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            validated_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---- Dummy Admin Credentials ----
ADMIN_USERNAME = "gibenjuri@gmail.com"
ADMIN_PASSWORD = "Zxcvbnm123!@"

# ---- Home Page ----
@app.route("/")
def home():
    return render_template("home.html", title=_("Home"))

# ---- Shop Page ----
@app.route("/shop")
def shop():
    return render_template("shop.html", title=_("Shop"))

# ---- News Page ----
@app.route("/news")
def news():
    return render_template("news.html", title=_("News"))

# ---- Verify Page ----
@app.route("/verify", methods=["GET", "POST"])
def verify():
    result = None
    if request.method == "POST":
        code = request.form.get("code", "").strip()

        conn = sqlite3.connect("codes.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, validated_at FROM codes WHERE code = ?", (code,))
        row = cursor.fetchone()

        if not code:
            result = {"status": "format_error"}
        elif row:
            if not row[1]:
                cursor.execute("UPDATE codes SET validated_at = datetime('now') WHERE id = ?", (row[0],))
                conn.commit()
                result = {"status": "success"}
            else:
                result = {"status": "used", "timestamp": row[1]}
        else:
            result = {"status": "not_real"}

        conn.close()

    return render_template("verify.html", title=_("Verify"), result=result)

# ---- Login Page ----
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            flash(_("Login successful ✅"), "success")
            return redirect(url_for("admin"))
        else:
            flash(_("Invalid username or password ❌"), "error")

    return render_template("login.html", title=_("Admin Login"))

# ---- Logout ----
@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    flash(_("You have been logged out."), "success")
    return redirect(url_for("login"))

# ---- Admin Dashboard ----
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("admin_logged_in"):
        flash(_("Please log in to access admin panel."), "error")
        return redirect(url_for("login"))

    conn = sqlite3.connect("codes.db")
    cursor = conn.cursor()

    if request.method == "POST":
        new_code = request.form.get("new_code")
        delete_id = request.form.get("delete_id")

        if new_code:
            try:
                cursor.execute("INSERT INTO codes (code) VALUES (?)", (new_code.strip(),))
                conn.commit()
                flash(_("New code added successfully."), "success")
            except sqlite3.IntegrityError:
                flash(_("This code already exists."), "error")

        if delete_id:
            cursor.execute("DELETE FROM codes WHERE id = ?", (delete_id,))
            conn.commit()
            flash(_("Code deleted successfully."), "success")

    cursor.execute("SELECT COUNT(*) FROM codes")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM codes WHERE validated_at IS NOT NULL")
    validated = cursor.fetchone()[0]

    remaining = total - validated

    cursor.execute("SELECT id, code, validated_at FROM codes ORDER BY id DESC")
    codes = cursor.fetchall()

    conn.close()

    return render_template("admin.html", title=_("Admin"),
                           total=total, validated=validated, remaining=remaining, codes=codes)

# ---- Admin Import ----
@app.route("/admin/import", methods=["POST"])
def admin_import():
    if not session.get("admin_logged_in"):
        flash(_("Unauthorized access."), "error")
        return redirect(url_for("login"))

    uploaded_file = request.files.get("file")
    if not uploaded_file or uploaded_file.filename == "":
        flash(_("No file selected!"), "error")
        return redirect(url_for("admin"))

    if not uploaded_file.filename.endswith(".xlsx"):
        flash(_("Invalid file format! Please upload an .xlsx file."), "error")
        return redirect(url_for("admin"))

    filename = secure_filename(uploaded_file.filename)
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    uploaded_file.save(save_path)

    try:
        wb = openpyxl.load_workbook(save_path)
        sheet = wb.active

        conn = sqlite3.connect("codes.db")
        cursor = conn.cursor()
        imported_count = 0

        for row in sheet.iter_rows(min_row=2, values_only=True):
            code = str(row[0]).strip() if row[0] else None
            if code:
                try:
                    cursor.execute("INSERT INTO codes (code) VALUES (?)", (code,))
                    imported_count += 1
                except sqlite3.IntegrityError:
                    continue

        conn.commit()
        conn.close()
        flash(_("Successfully imported %(count)d codes.", count=imported_count), "success")

    except Exception as e:
        flash(_("Error while importing: %(error)s", error=str(e)), "error")

    return redirect(url_for("admin"))

# ---- Run App ----
if __name__ == "__main__":
    app.run(debug=True)
