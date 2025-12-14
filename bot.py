import psycopg2
from psycopg2.extras import RealDictCursor
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
import time

API_TOKEN = "6872510077:AAFtVniM9OJRPDkjozI8hU52AvoDZ7njtsI"
ADMIN_USERNAME = "MD18073"
DATABASE_URL = "postgresql://postgres:wTWqoVJnKEDRtDDWFlpJNfSGGRdYCJHB@nozomi.proxy.rlwy.net:22169/railway"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

def get_db():
    # Retry logic if database not ready yet
    for i in range(5):
        try:
            return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        except Exception as e:
            print("DB CONNECTION ERROR, retrying...", e)
            time.sleep(3)
    raise Exception("Could not connect to database after retries")

# Start, language selection, show services, buy service, admin panel...
# (same as previous bot.py code)
