import os
import psycopg2
from flask import Flask, request, redirect, session, render_template_string

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

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        balance NUMERIC DEFAULT 0,
        total_added NUMERIC DEFAULT 0,
        total_spent NUMERIC DEFAULT 0,
        lang TEXT
    )
    """)

    # SERVICES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        price NUMERIC NOT NULL
    )
    """)

    # TOPUPS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS topups (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        amount NUMERIC,
        method TEXT,
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

    # USERS STATS
    cur.execute("""
        SELECT user_id, balance, total_added, total_spent
        FROM users
        ORDER BY user_id DESC
    """)
    users = cur.fetchall()

    # SERVICES
    cur.execute("SELECT * FROM services ORDER BY id DESC")
    services = cur.fetchall()

    # TOPUPS
    cur.execute("""
        SELECT id, user_id, amount, method, status
        FROM topups
        ORDER BY id DESC
    """)
    topups = cur.fetchall()

    conn.close()

    return render_template_string("""
    <h1>Admin Dashboard</h1>

    <h2>Add Service</h2>
    <form method="post" action="/add_service">
        <input name="name" placeholder="Service name" required>
        <input name="price" type="number" step="0.01" placeholder="Price" required>
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
            User {{ t[1] }} | ${{ t[2] }} | {{ t[3] }} | {{ t[4] }}
            {% if t[4] == 'pending' %}
                <a href="/approve/{{ t[0] }}">Approve</a> |
                <a href="/reject/{{ t[0] }}">Reject</a>
            {% endif %}
        </li>
    {% endfor %}
    </ul>

    <h2>User Statistics</h2>
    <ul>
    {% for u in users %}
        <li>
            User {{ u[0] }} |
            Balance: ${{ u[1] }} |
            Added: ${{ u[2] }} |
            Spent: ${{ u[3] }}
        </li>
    {% endfor %}
    </ul>

    <br>
    <a href="/logout">Logout</a>
    """, users=users, services=services, topups=topups)

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

# ================= APPROVE TOPUP ==========
@app.route("/approve/<int:tid>")
def approve(tid):
    if not session.get("admin"):
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT user_id, amount FROM topups WHERE id=%s", (tid,))
    row = cur.fetchone()

    if row:
        user_id, amount = row

        cur.execute("UPDATE topups SET status='approved' WHERE id=%s", (tid,))
        cur.execute("""
            UPDATE users
            SET balance = balance + %s,
                total_added = total_added + %s
            WHERE user_id=%s
        """, (amount, amount, user_id))

    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ================= REJECT TOPUP ===========
@app.route("/reject/<int:tid>")
def reject(tid):
    if not session.get("admin"):
        return redirect("/")

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
    app.run(host="0.0.0.0", port=8080)
