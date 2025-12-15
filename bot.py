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
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 PayPal Services", callback_data="cat_paypal")],
        [InlineKeyboardButton(text="💳 SSN Services", callback_data="cat_ssn")],
        [InlineKeyboardButton(text="💳 Visa Card", callback_data="cat_visa")],
        [InlineKeyboardButton(text="📧 Email", callback_data="cat_email")],
        [InlineKeyboardButton(text="💰 Balance", callback_data="balance")]
    ])

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
            [InlineKeyboardButton("PayPal USA", callback_data="sub_us")],
            [InlineKeyboardButton("PayPal Canada", callback_data="sub_ca")],
            [InlineKeyboardButton("PayPal UK", callback_data="sub_uk")],
            back_button
        ]
        await call.message.edit_text(
            "Select PayPal region:" if lang=="en" else "اختر منطقة بايبال",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    else:
        await call.message.answer("Category not implemented yet.")
        await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[back_button]))

# ================= SUB-CATEGORIES =================
@dp.callback_query(lambda c: c.data.startswith("sub_"))
async def show_subcategory(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (call.from_user.id,))
    lang = cur.fetchone()[0]
    conn.close()

    back_button = [InlineKeyboardButton("⬅️ Back" if lang=="en" else "⬅️ رجوع", callback_data="cat_paypal")]

    buttons = [
        [InlineKeyboardButton("PayPal Linked SSN", callback_data="buy_ssn")],
        [InlineKeyboardButton("PayPal Linked Bank", callback_data="buy_bank")],
        [InlineKeyboardButton("PayPal Linked Visa", callback_data="buy_visa")],
        back_button
    ]

    await call.message.edit_text(
        "Select service:" if lang=="en" else "اختر الخدمة",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

# ================= PURCHASE CONFIRM =================
@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def purchase_service(call: types.CallbackQuery):
    service_map = {
        "buy_ssn": "PayPal Linked SSN",
        "buy_bank": "PayPal Linked Bank",
        "buy_visa": "PayPal Linked Visa"
    }

    service_name = service_map.get(call.data)
    if not service_name:
        return

    # In real scenario, check balance and deduct
    await call.message.answer(f"✅ You are about to buy: {service_name}\nPlease confirm or cancel.")

# ================= BACK TO MAIN MENU =================
@dp.callback_query(lambda c: c.data == "main_menu")
async def go_main(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (call.from_user.id,))
    lang = cur.fetchone()[0]
    conn.close()
    await call.message.edit_text(
        "Main Menu" if lang=="en" else "القائمة الرئيسية",
        reply_markup=main_menu(lang)
    )

# ================= BALANCE ====================
@dp.callback_query(lambda c: c.data == "balance")
async def balance(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lang, balance FROM users WHERE user_id=%s", (call.from_user.id,))
    lang, balance = cur.fetchone()
    conn.close()

    await call.message.answer(f"💰 Balance: ${balance}" if lang=="en" else f"💰 الرصيد: ${balance}\nSend top-up request with amount.")

# ================= RUN =====================
async def main():
    print("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
