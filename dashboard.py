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

# ================= DATABASE =================
def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        category TEXT,
        name TEXT,
        message TEXT,
        price NUMERIC
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS topups (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        amount NUMERIC,
        status TEXT DEFAULT 'pending',
        method TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        balance NUMERIC DEFAULT 0,
        total_added NUMERIC DEFAULT 0,
        total_spent NUMERIC DEFAULT 0
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

# ================= DASHBOARD ==================
@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM services ORDER BY id DESC")
    services = cur.fetchall()

    cur.execute("SELECT * FROM products ORDER BY id DESC")
    products = cur.fetchall()

    cur.execute("SELECT * FROM topups ORDER BY id DESC")
    topups = cur.fetchall()

    cur.execute("SELECT * FROM users ORDER BY user_id DESC")
    users = cur.fetchall()

    conn.close()

    return render_template_string("""
    <h1>Admin Dashboard</h1>

    <h2>Add Service</h2>
    <form method="post" action="/add_service">
        <input name="name" placeholder="Service name" required>
        <button>Add</button>
    </form>

    <h2>Delete Service</h2>
    <form method="post" action="/delete_service">
        <select name="service_id" required>
        {% for s in services %}
            <option value="{{ s[0] }}">{{ s[1] }}</option>
        {% endfor %}
        </select>
        <button>Delete</button>
    </form>

    <h2>Add Product</h2>
    <form method="post" action="/add_product">
        <input name="category" placeholder="Category (Top-level)" required>
        <input name="name" placeholder="Product name" required>
        <input name="price" placeholder="Price" type="number" step="0.01" required>
        <textarea name="message" placeholder="Message to send user" required></textarea>
        <button>Add</button>
    </form>

    <h2>Products</h2>
    <ul>
        {% for p in products %}
        <li>{{ p[2] }} ({{ p[1] }}) - ${{ p[4] }}</li>
        {% endfor %}
    </ul>

    <h2>Top-up Requests</h2>
    <ul>
        {% for t in topups %}
        <li>
            User {{ t[1] }} — ${{ t[2] }} — {{ t[4] }}
            {% if t[4] == 'pending' %}
            <a href="/approve/{{ t[0] }}">Approve</a> |
            <a href="/reject/{{ t[0] }}">Reject</a>
            {% endif %}
        </li>
        {% endfor %}
    </ul>

    <h2>Users Statistics</h2>
    <table border="1" cellpadding="5">
        <tr><th>User ID</th><th>Balance</th><th>Total Added</th><th>Total Spent</th></tr>
        {% for u in users %}
        <tr>
            <td>{{ u[0] }}</td>
            <td>{{ u[1] }}</td>
            <td>{{ u[2] }}</td>
            <td>{{ u[3] }}</td>
        </tr>
        {% endfor %}
    </table>

    <br><a href="/logout">Logout</a>
    """, services=services, products=products, topups=topups, users=users)

# ================= ADD / DELETE SERVICE ==================
@app.route("/add_service", methods=["POST"])
def add_service():
    if not session.get("admin"):
        return redirect("/")
    name = request.form["name"]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO services (name) VALUES (%s)", (name,))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

@app.route("/delete_service", methods=["POST"])
def delete_service():
    if not session.get("admin"):
        return redirect("/")
    service_id = request.form["service_id"]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM services WHERE id=%s", (service_id,))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ================= ADD PRODUCT ==================
@app.route("/add_product", methods=["POST"])
def add_product():
    if not session.get("admin"):
        return redirect("/")
    category = request.form["category"]
    name = request.form["name"]
    message = request.form["message"]
    price = request.form["price"]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO products (category, name, message, price) VALUES (%s,%s,%s,%s)",
                (category, name, message, price))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ================= TOPUP ACTIONS ==================
@app.route("/approve/<int:tid>")
def approve(tid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE topups SET status='approved' WHERE id=%s RETURNING user_id, amount", (tid,))
    row = cur.fetchone()
    if row:
        user_id, amount = row
        # update user balance
        cur.execute("UPDATE users SET balance=balance+%s, total_added=total_added+%s WHERE user_id=%s",
                    (amount, amount, user_id))
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

# ================= LOGOUT ==================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ================= RUN ==================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
