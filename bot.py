import asyncio
import os
import psycopg2
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================
BOT_TOKEN = "6872510077:AAFtVniM9OJRPDkjozI8hU52AvoDZ7njtsI"
ADMIN_USERNAME = "MD18073"
CHANNEL_USERNAME = "@Offerwallproxy"

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
    # users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        lang TEXT,
        balance NUMERIC DEFAULT 0
    )""")
    # topups table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS topups (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        amount NUMERIC,
        status TEXT DEFAULT 'pending',
        method TEXT DEFAULT 'Unknown'
    )""")
    # products table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        category TEXT,
        name TEXT,
        price NUMERIC,
        message TEXT
    )""")
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
    kb = InlineKeyboardMarkup()
    if lang == "ar":
        kb.add(InlineKeyboardButton(text="🛒 الخدمات", callback_data="services"))
        kb.add(InlineKeyboardButton(text="💰 الرصيد", callback_data="balance"))
    else:
        kb.add(InlineKeyboardButton(text="🛒 Services", callback_data="services"))
        kb.add(InlineKeyboardButton(text="💰 Balance", callback_data="balance"))
    return kb

def back_button(lang):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back" if lang=="en" else "🔙 العودة", callback_data="back")]
    ])

# ================= START ====================
@dp.message(CommandStart())
async def start(message: types.Message):
    # Check subscription
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, message.from_user.id)
        if member.status in ["left", "kicked"]:
            await message.answer(f"⚠️ Please join {CHANNEL_USERNAME} to use the bot.")
            return
    except:
        await message.answer(f"⚠️ Please join {CHANNEL_USERNAME} to use the bot.")
        return

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (message.from_user.id,))
    conn.commit()
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (message.from_user.id,))
    row = cur.fetchone()
    conn.close()

    if row and row[0]:
        lang = row[0]
        await message.answer("Main Menu" if lang=="en" else "القائمة الرئيسية", reply_markup=main_menu(lang))
    else:
        await message.answer("Choose language / اختر اللغة", reply_markup=lang_keyboard())

# ================= LANGUAGE =================
@dp.callback_query(lambda c: c.data.startswith("lang_"))
async def set_language(call):
    lang = call.data.split("_")[1]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET lang=%s WHERE user_id=%s", (lang, call.from_user.id))
    conn.commit()
    conn.close()
    await call.message.edit_text("Main Menu" if lang=="en" else "القائمة الرئيسية", reply_markup=main_menu(lang))

# ================= BALANCE =================
@dp.callback_query(lambda c: c.data == "balance")
async def balance_menu(call):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lang, balance FROM users WHERE user_id=%s", (call.from_user.id,))
    lang, balance = cur.fetchone()
    conn.close()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Top-up via Binance", callback_data="topup_Binance")],
        [InlineKeyboardButton(text="💰 Top-up via CoinEX", callback_data="topup_CoinEX")],
        [InlineKeyboardButton(text="💰 Top-up via Crypto", callback_data="topup_Crypto")],
        [InlineKeyboardButton(text="🔙 Back" if lang=="en" else "🔙 العودة", callback_data="back")]
    ])
    await call.message.edit_text(f"💰 Balance: ${balance}", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("topup_"))
async def topup_method(call):
    method = call.data.split("_")[1]
    await call.message.answer(f"Send amount to top-up via {method}:")
    # Store the method temporarily in user session
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET lang=lang WHERE user_id=%s", (call.from_user.id,))  # dummy update
    conn.commit()
    conn.close()

@dp.message(lambda m: m.text.isdigit())
async def create_topup(message: types.Message):
    amount = int(message.text)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id=%s", (message.from_user.id,))
    user = cur.fetchone()
    if not user:
        await message.answer("⚠️ You are not registered.")
        conn.close()
        return
    cur.execute("INSERT INTO topups (user_id, amount, method) VALUES (%s,%s,%s)",
                (message.from_user.id, amount, "Unknown"))
    conn.commit()
    conn.close()
    await message.answer("✅ Top-up request sent. Wait for admin approval.")

# ================= BACK =================
@dp.callback_query(lambda c: c.data == "back")
async def go_back(call):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (call.from_user.id,))
    lang = cur.fetchone()[0]
    conn.close()
    await call.message.edit_text("Main Menu" if lang=="en" else "القائمة الرئيسية", reply_markup=main_menu(lang))

# ================= RUN =====================
async def main():
    print("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
