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
dp = Dispatcher(bot)

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
        lang TEXT,
        balance NUMERIC DEFAULT 0
    )
    """)

    # Topups table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS topups (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        amount NUMERIC,
        method TEXT,
        status TEXT DEFAULT 'pending'
    )
    """)

    # Services table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id SERIAL PRIMARY KEY,
        name TEXT,
        category TEXT,
        subcategory TEXT,
        price NUMERIC
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= KEYBOARDS =================
def lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🇱🇧 العربية", callback_data="lang_ar")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
    ])

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("💳 PayPal Services", callback_data="category_paypal")],
        [InlineKeyboardButton("🆔 SSN Services", callback_data="category_ssn")],
        [InlineKeyboardButton("💳 Visa Card", callback_data="category_visa")],
        [InlineKeyboardButton("📧 Email", callback_data="category_email")],
        [InlineKeyboardButton("💰 Balance", callback_data="balance")]
    ])

def subcategory_keyboard(category):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT subcategory FROM services WHERE category=%s", (category,))
    subs = cur.fetchall()
    conn.close()
    buttons = [[InlineKeyboardButton(sub[0], callback_data=f"sub_{sub[0]}")] for sub in subs]
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def products_keyboard(subcategory):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price FROM services WHERE subcategory=%s", (subcategory,))
    products = cur.fetchall()
    conn.close()
    buttons = [[InlineKeyboardButton(f"{p[1]} — ${p[2]}", callback_data=f"buy_{p[0]}")] for p in products]
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"back_category")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def balance_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Binance", callback_data="topup_binance")],
        [InlineKeyboardButton("CoinEX", callback_data="topup_coinex")],
        [InlineKeyboardButton("Crypto", callback_data="topup_crypto")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ])

# ================= START ====================
@dp.message(CommandStart())
async def start(message: types.Message):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=%s", (message.from_user.id,))
    user = cur.fetchone()
    if not user:
        # First time user: choose language
        cur.execute("INSERT INTO users (user_id) VALUES (%s)", (message.from_user.id,))
        conn.commit()
        await message.answer("Choose language / اختر اللغة", reply_markup=lang_keyboard())
    else:
        await message.answer("Main Menu", reply_markup=main_menu())
    conn.close()

# ================= LANGUAGE =================
@dp.callback_query(lambda c: c.data.startswith("lang_"))
async def set_language(call: types.CallbackQuery):
    lang = call.data.split("_")[1]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET lang=%s WHERE user_id=%s", (lang, call.from_user.id))
    conn.commit()
    conn.close()
    await call.message.edit_text("Main Menu" if lang=="en" else "القائمة الرئيسية", reply_markup=main_menu())
    await call.answer()

# ================= MAIN MENU CALLBACKS =================
@dp.callback_query(lambda c: c.data.startswith("category_"))
async def category_click(call: types.CallbackQuery):
    category = call.data.split("_")[1]
    await call.message.edit_text(f"Select {category} subcategory", reply_markup=subcategory_keyboard(category))
    await call.answer()

@dp.callback_query(lambda c: c.data.startswith("sub_"))
async def subcategory_click(call: types.CallbackQuery):
    sub = call.data.split("_")[1]
    await call.message.edit_text(f"Select product in {sub}", reply_markup=products_keyboard(sub))
    await call.answer()

@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy_product(call: types.CallbackQuery):
    product_id = int(call.data.split("_")[1])
    conn = get_db()
    cur = conn.cursor()
    # Get user balance and product price
    cur.execute("SELECT balance FROM users WHERE user_id=%s", (call.from_user.id,))
    balance = cur.fetchone()[0]
    cur.execute("SELECT name, price FROM services WHERE id=%s", (product_id,))
    name, price = cur.fetchone()
    if balance >= price:
        cur.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s", (price, call.from_user.id))
        conn.commit()
        await call.message.answer(f"✅ You purchased {name} for ${price}. New balance: ${balance-price}")
    else:
        await call.message.answer(f"❌ Not enough balance. Product price: ${price}, Your balance: ${balance}")
    conn.close()
    await call.answer()

# ================= BALANCE =================
@dp.callback_query(lambda c: c.data.startswith("topup_"))
async def topup_method(call: types.CallbackQuery):
    method = call.data.split("_")[1]
    await call.message.answer(f"Send amount for {method} topup. Admin will approve manually.")
    await call.answer()

@dp.callback_query(lambda c: c.data=="balance")
async def balance_click(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT balance FROM users WHERE user_id=%s", (call.from_user.id,))
    balance = cur.fetchone()[0]
    conn.close()
    await call.message.answer(f"💰 Your balance: ${balance}", reply_markup=balance_keyboard())
    await call.answer()

# ================= BACK BUTTONS =================
@dp.callback_query(lambda c: c.data=="back_main")
async def back_main(call: types.CallbackQuery):
    await call.message.edit_text("Main Menu", reply_markup=main_menu())
    await call.answer()

@dp.callback_query(lambda c: c.data=="back_category")
async def back_category(call: types.CallbackQuery):
    await call.message.edit_text("Select category", reply_markup=main_menu())
    await call.answer()

# ================= RUN =====================
async def main():
    print("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
