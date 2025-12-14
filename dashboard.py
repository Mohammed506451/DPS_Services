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
    return "Dashboard is running ✅"

@app.route("/db-test")
def db_test():
    try:
        conn = get_db()
        conn.close()
        return "Database connected ✅"
    except Exception as e:
        return f"DB ERROR: {e}"

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT)
