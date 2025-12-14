import os
import psycopg2
from flask import Flask, request, redirect, url_for, session, render_template_string

# ================= CONFIG =================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:wTWqoVJnKEDRtDDWFlpJNfSGGRdYCJHB@nozomi.proxy.rlwy.net:22169/railway"
)

ADMIN_PASSWORD = "Mohammed@7756"
SECRET_KEY = "super-secret-key"

# ================= APP ====================
app = Flask(__name__)
app.secret_key = SECRET_KEY

# ================= DATABASE ===============
def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        price NUMERIC NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS topups (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        amount NUMERIC,
        status TEXT DEFAULT 'pending'
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= LOGIN ==================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/dashboard")
    return render_template_string("""
    <h2>Admin Login</h2>
    <form method="post">
        <input type="password" name="password" placeholder="Password" required>
        <button type="submit">Login</button>
    </form>
    """)

# ================= DASHBOARD ==============
@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM services ORDER BY id DESC")
    services = cur.fetchall()

    cur.execute("SELECT * FROM topups ORDER BY id DESC")
    topups = cur.fetchall()

    conn.close()

    return render_template_string("""
    <h1>Admin Dashboard</h1>

    <h2>Add Service</h2>
    <form method="post" action="/add_service">
        <input name="name" placeholder="Service name" required>
        <input name="price" placeholder="Price" type="number" step="0.01" required>
        <button>Add</button>
    </form>

    <h2>Services</h2>
    <ul>
        {% for s in services %}
        <li>{{ s[1] }} — ${{ s[2] }}</li>
        {% endfor %}
    </ul>

    <h2>Top-up Requests</h2>
    <ul>
        {% for t in topups %}
        <li>
            User {{ t[1] }} — ${{ t[2] }} — {{ t[3] }}
            {% if t[3] == 'pending' %}
            <a href="/approve/{{ t[0] }}">Approve</a> |
            <a href="/reject/{{ t[0] }}">Reject</a>
            {% endif %}
        </li>
        {% endfor %}
    </ul>

    <br><a href="/logout">Logout</a>
    """, services=services, topups=topups)

# ================= ADD SERVICE ============
@app.route("/add_service", methods=["POST"])
def add_service():
    if not session.get("admin"):
        return redirect("/")

    name = request.form["name"]
    price = request.form["price"]

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO services (name, price) VALUES (%s, %s)", (name, price))
    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ================= TOPUP ACTIONS ==========
@app.route("/approve/<int:tid>")
def approve(tid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE topups SET status='approved' WHERE id=%s", (tid,))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

@app.route("/reject/<int:tid>")
def reject(tid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE topups SET status='rejected' WHERE id=%s", (tid,))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ================= RUN ====================
if __name__ == "__main__":
    app.run()
