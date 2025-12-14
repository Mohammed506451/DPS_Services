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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        balance NUMERIC DEFAULT 0,
        lang TEXT
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
    CREATE TABLE IF NOT EXISTS services (
        id SERIAL PRIMARY KEY,
        category TEXT,
        name TEXT,
        price NUMERIC
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
    buttons = [
        [InlineKeyboardButton(text="💳 PayPal Services" if lang=="en" else "💳 بايبال", callback_data="cat_paypal")],
        [InlineKeyboardButton(text="🆔 SSN Services" if lang=="en" else "🆔 اس ان", callback_data="cat_ssn")],
        [InlineKeyboardButton(text="💳 Visa Card" if lang=="en" else "💳 بطاقة فيزا", callback_data="cat_visa")],
        [InlineKeyboardButton(text="📧 Email" if lang=="en" else "📧 البريد الالكتروني", callback_data="cat_email")],
        [InlineKeyboardButton(text="💰 Balance" if lang=="en" else "💰 الرصيد", callback_data="balance")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ================= START ====================
@dp.message(CommandStart())
async def start(message: types.Message):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (message.from_user.id,))
    conn.commit()
    conn.close()

    await message.answer(
        "Choose language / اختر اللغة",
        reply_markup=lang_keyboard()
    )

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

# ================= CATEGORIES =================
@dp.callback_query(lambda c: c.data.startswith("cat_"))
async def show_category(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (call.from_user.id,))
    lang = cur.fetchone()[0]
    conn.close()

    back_button = [InlineKeyboardButton("⬅️ Back" if lang=="en" else "⬅️ رجوع", callback_data="main_menu")]

    if call.data == "cat_paypal":
        buttons = [
            [InlineKeyboardButton("USA PayPal", callback_data="sub_us")],
            [InlineKeyboardButton("UK PayPal", callback_data="sub_uk")],
            [InlineKeyboardButton("Canada PayPal", callback_data="sub_ca")],
            back_button
        ]
        await call.message.edit_text("Select PayPal region:" if lang=="en" else "اختر منطقة بايبال", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        # Placeholder for other categories
        await call.message.answer("Category not implemented yet.")
        await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[back_button]))

# ================= BACK TO MAIN MENU =================
@dp.callback_query(lambda c: c.data=="main_menu")
async def back_main(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (call.from_user.id,))
    lang = cur.fetchone()[0]
    conn.close()

    await call.message.edit_text("Main Menu" if lang=="en" else "القائمة الرئيسية",
                                 reply_markup=main_menu(lang))

# ================= BALANCE / TOPUP =================
@dp.callback_query(lambda c: c.data=="balance")
async def show_balance(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT balance FROM users WHERE user_id=%s", (call.from_user.id,))
    balance = cur.fetchone()[0]
    conn.close()

    await call.message.answer(f"💰 Your balance: ${balance}" if balance is not None else "💰 الرصيد: 0")

# ================= RUN =====================
async def main():
    print("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
