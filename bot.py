import asyncio
import os
import psycopg2
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================
BOT_TOKEN = "6872510077:AAFtVniM9OJRPDkjozI8hU52AvoDZ7njtsI"
ADMIN_USERNAME = "MD18073"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:wTWqoVJnKEDRtDDWFlpJNfSGGRdYCJHB@nozomi.proxy.rlwy.net:22169/railway"
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ================= DATABASE =================
def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    conn = get_db()
    cur = conn.cursor()
    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        username TEXT,
        balance NUMERIC DEFAULT 0,
        lang TEXT
    )
    """)
    # Services table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        price NUMERIC NOT NULL
    )
    """)
    # Top-ups table
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

# ================= KEYBOARDS =================
def lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇱🇧 العربية", callback_data="lang_ar")],
        [InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_en")]
    ])

def main_menu(lang):
    if lang == "ar":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 الخدمات", callback_data="services")],
            [InlineKeyboardButton(text="💰 شحن الرصيد", callback_data="topup")]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Services", callback_data="services")],
            [InlineKeyboardButton(text="💰 Top up balance", callback_data="topup")]
        ])

# ================= START ====================
@dp.message(CommandStart())
async def start(message: types.Message):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO users (user_id, username) VALUES (%s, %s)
    ON CONFLICT (user_id) DO NOTHING
    """, (message.from_user.id, message.from_user.username))
    conn.commit()
    conn.close()

    await message.answer("Choose language / اختر اللغة", reply_markup=lang_keyboard())

# ================= LANGUAGE =================
@dp.callback_query(lambda c: c.data.startswith("lang_"))
async def set_language(call: types.CallbackQuery):
    lang = call.data.split("_")[1]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET lang=%s WHERE user_id=%s", (lang, call.from_user.id))
    conn.commit()
    conn.close()

    await call.message.edit_text(
        "Main Menu" if lang == "en" else "القائمة الرئيسية",
        reply_markup=main_menu(lang)
    )

# ================= SERVICES =================
@dp.callback_query(lambda c: c.data == "services")
async def show_services(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lang, balance FROM users WHERE user_id=%s", (call.from_user.id,))
    lang, balance = cur.fetchone()

    cur.execute("SELECT name, price FROM services ORDER BY id")
    services = cur.fetchall()
    conn.close()

    if not services:
        await call.message.answer("No services available" if lang=="en" else "لا توجد خدمات")
        return

    text = "🛒 Services:\n\n" if lang=="en" else "🛒 الخدمات:\n\n"
    for s in services:
        text += f"{s[0]} — ${s[1]}\n"

    text += f"\n💰 Balance: ${balance}"
    await call.message.answer(text)

# ================= TOPUP ====================
@dp.callback_query(lambda c: c.data == "topup")
async def topup(call: types.CallbackQuery):
    await call.message.answer(
        "Send amount like: 10\nAdmin will approve manually" 
        if True else ""
    )

@dp.message(lambda m: m.text and m.text.isdigit())
async def create_topup(message: types.Message):
    amount = int(message.text)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO topups (user_id, amount) VALUES (%s, %s)", (message.from_user.id, amount))
    conn.commit()
    conn.close()
    await message.answer("✅ Top-up request sent. Wait for admin approval.")

# ================= RUN =====================
async def main():
    print("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
