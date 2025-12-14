import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, redirect

app = Flask(__name__)
ADMIN_PASSWORD = "Mohammed@7756"

DATABASE_URL = os.environ.get("DATABASE_URL")

# ===== DATABASE CONNECTION =====
def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# ===== INITIALIZE DATABASE =====
def init_db():
    conn = get_db()
    cur = conn.cursor()
    # Auto-create tables if missing
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS topup_requests (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            username TEXT,
            amount REAL,
            status TEXT DEFAULT 'pending'
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT,
            price REAL
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            return redirect("/topups")
        return "<h3>❌ Wrong password</h3>"
    return """
    <h2>Admin Login</h2>
    <form method="post">
        <input type="password" name="password" placeholder="Password" required>
        <br><br>
        <button type="submit">Login</button>
    </form>
    """

# Note: Add /topups, /approve, /reject, /products, /delete routes as needed
# Example: use the previous dashboard.py code I gave you

if __name__ == "__main__":
    from waitress import serve
    port = int(os.environ.get("PORT", 8080))
    serve(app, host="0.0.0.0", port=port)
