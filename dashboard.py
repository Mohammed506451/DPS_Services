import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, redirect

app = Flask(__name__)
ADMIN_PASSWORD = "Mohammed@7756"

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

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

@app.route("/topups")
def topups():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM topup_requests")
    rows = cur.fetchall()
    conn.close()
    html = "<h2>Top-up Requests</h2><table border='1' cellpadding='5'><tr><th>ID</th><th>Username</th><th>Amount</th><th>Status</th><th>Action</th></tr>"
    for r in rows:
        html += f"<tr><td>{r['id']}</td><td>{r['username']}</td><td>{r['amount']}</td><td>{r['status']}</td><td>"
        if r["status"] == "pending":
            html += f"<a href='/approve/{r['id']}'>Approve</a> | <a href='/reject/{r['id']}'>Reject</a>"
        html += "</td></tr>"
    html += "</table><br><a href='/products'>Manage Services</a>"
    return html

@app.route("/approve/<int:rid>")
def approve(rid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT user_id, amount FROM topup_requests WHERE id=%s", (rid,))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE users SET balance = balance + %s WHERE user_id=%s", (row["amount"], row["user_id"]))
        cur.execute("UPDATE topup_requests SET status='approved' WHERE id=%s", (rid,))
        conn.commit()
    conn.close()
    return redirect("/topups")

@app.route("/reject/<int:rid>")
def reject(rid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE topup_requests SET status='rejected' WHERE id=%s", (rid,))
    conn.commit()
    conn.close()
    return redirect("/topups")

@app.route("/products", methods=["GET", "POST"])
def products():
    conn = get_db()
    cur = conn.cursor()
    if request.method == "POST":
        name = request.form.get("name")
        price = request.form.get("price")
        cur.execute("INSERT INTO products (name, price) VALUES (%s,%s)", (name, price))
        conn.commit()
    cur.execute("SELECT * FROM products")
    rows = cur.fetchall()
    conn.close()

    html = "<h2>Services</h2><table border='1' cellpadding='5'><tr><th>ID</th><th>Name</th><th>Price</th><th>Action</th></tr>"
    for r in rows:
        html += f"<tr><td>{r['id']}</td><td>{r['name']}</td><td>{r['price']}</td><td><a href='/delete/{r['id']}'>Delete</a></td></tr>"
    html += "</table>"

    html += """
    <br>
    <h3>Add Service</h3>
    <form method="post">
        <input name="name" placeholder="Service name" required>
        <br><br>
        <input name="price" type="number" step="0.01" placeholder="Price" required>
        <br><br>
        <button type="submit">Add</button>
    </form>
    <br>
    <a href="/topups">Back to Top-ups</a>
    """
    return html

@app.route("/delete/<int:pid>")
def delete(pid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id=%s", (pid,))
    conn.commit()
    conn.close()
    return redirect("/products")

if __name__ == "__main__":
    from waitress import serve
    port = int(os.environ.get("PORT", 8080))
    serve(app, host="0.0.0.0", port=port)
