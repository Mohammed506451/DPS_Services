import os
import psycopg2
from flask import Flask, request, redirect, session, render_template_string

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:wTWqoVJnKEDRtDDWFlpJNfSGGRdYCJHB@nozomi.proxy.rlwy.net:22169/railway"
)

ADMIN_PASSWORD = "Mohammed@7756"

app = Flask(__name__)
app.secret_key = "super-secret-key"

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST" and request.form["password"] == ADMIN_PASSWORD:
        session["admin"] = True
        return redirect("/dashboard")
    return render_template_string("""
    <h2>Admin Login</h2>
    <form method="post">
      <input type="password" name="password" required>
      <button>Login</button>
    </form>
    """)

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
    <h1>Dashboard</h1>

    <h2>Add Service</h2>
    <form method="post" action="/add_service">
      <input name="name" required>
      <input name="price" type="number" step="0.01" required>
      <button>Add</button>
    </form>

    <h2>Services</h2>
    <ul>{% for s in services %}<li>{{s[1]}} - ${{s[2]}}</li>{% endfor %}</ul>

    <h2>Top-ups</h2>
    <ul>
    {% for t in topups %}
      <li>
        User {{t[1]}} | ${{t[2]}} | {{t[3]}}
        {% if t[3]=='pending' %}
          <a href="/approve/{{t[0]}}">Approve</a>
          <a href="/reject/{{t[0]}}">Reject</a>
        {% endif %}
      </li>
    {% endfor %}
    </ul>

    <a href="/logout">Logout</a>
    """, services=services, topups=topups)

@app.route("/add_service", methods=["POST"])
def add_service():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO services (name, price) VALUES (%s,%s)",
                (request.form["name"], request.form["price"]))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

@app.route("/approve/<int:tid>")
def approve(tid):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT user_id, amount FROM topups WHERE id=%s", (tid,))
    user_id, amount = cur.fetchone()

    cur.execute("UPDATE users SET balance = balance + %s WHERE user_id=%s",
                (amount, user_id))
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

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
