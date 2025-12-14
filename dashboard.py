import os
import psycopg2
from flask import Flask

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:wTWqoVJnKEDRtDDWFlpJNfSGGRdYCJHB@nozomi.proxy.rlwy.net:22169/railway"
)

app = Flask(__name__)

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

@app.route("/")
def home():
    try:
        conn = get_db()
        cur = conn.cursor()
        # Check tables
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        tables = cur.fetchall()
        conn.close()
        return f"Tables: {tables}"
    except Exception as e:
        return f"DB ERROR: {e}"

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
