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

CHANNEL_ID = "@Offerwallproxy"

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
        lang TEXT,
        total_added NUMERIC DEFAULT 0,
        total_spent NUMERIC DEFAULT 0
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
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        category TEXT,
        name TEXT,
        message TEXT,
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

def services_keyboard(category=None):
    conn = get_db()
    cur = conn.cursor()
    keyboard = InlineKeyboardMarkup(row_width=1)
    if category is None:
        # Top-level categories
        buttons = ["PayPal Services", "SSN Services", "Visa Card", "Email"]
    else:
        cur.execute("SELECT name FROM products WHERE category=%s", (category,))
        buttons = [r[0] for r in cur.fetchall()]
        keyboard.add(InlineKeyboardButton(text="⬅️ Back", callback_data="services"))
    for b in buttons:
        keyboard.add(InlineKeyboardButton(text=b, callback_data=f"product_{b}_{category or ''}"))
    conn.close()
    return keyboard

def confirm_keyboard(price, product_name):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"✅ Confirm (${price})", callback_data=f"confirm_{product_name}"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")
        ]
    ])

# ================= START ====================
@dp.message(CommandStart())
async def start(message: types.Message):
    # Check subscription
    member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=message.from_user.id)
    if member.status == "left":
        await message.answer(f"Please join our channel {CHANNEL_ID} to use the bot.")
        return

    # Add user if not exists
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (message.from_user.id,))
    conn.commit()
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (message.from_user.id,))
    lang_row = cur.fetchone()
    conn.close()
    if lang_row and lang_row[0]:
        # Already selected language, show main menu
        lang = lang_row[0]
        await message.answer("Main Menu" if lang == "en" else "القائمة الرئيسية",
                             reply_markup=main_menu(lang))
    else:
        # Ask language
        await message.answer("Choose language / اختر اللغة",
                             reply_markup=lang_keyboard())

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
@dp.callback_query(lambda c: c.data.startswith("product_"))
async def select_product(call: types.CallbackQuery):
    _, product_name, category = call.data.split("_", 2)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT message, price FROM products WHERE name=%s", (product_name,))
    row = cur.fetchone()
    conn.close()
    if row:
        message_text, price = row
        await call.message.answer(
            f"Product: {product_name}\nPrice: ${price}\n\nDo you want to buy?",
            reply_markup=confirm_keyboard(price, product_name)
        )

@dp.callback_query(lambda c: c.data.startswith("confirm_"))
async def confirm_purchase(call: types.CallbackQuery):
    product_name = call.data.split("_", 1)[1]
    conn = get_db()
    cur = conn.cursor()
    # Get product price
    cur.execute("SELECT price FROM products WHERE name=%s", (product_name,))
    row = cur.fetchone()
    if not row:
        await call.message.answer("Product not found!")
        conn.close()
        return
    price = row[0]
    # Check user balance
    cur.execute("SELECT balance FROM users WHERE user_id=%s", (call.from_user.id,))
    balance = cur.fetchone()[0]
    if balance < price:
        await call.message.answer("❌ Not enough balance.")
        conn.close()
        return
    # Deduct balance
    cur.execute("UPDATE users SET balance=balance-%s, total_spent=total_spent+%s WHERE user_id=%s",
                (price, price, call.from_user.id))
    conn.commit()
    conn.close()
    await call.message.answer(f"✅ Purchase successful! ${price} deducted from your balance.")

@dp.callback_query(lambda c: c.data == "cancel")
async def cancel_purchase(call: types.CallbackQuery):
    await call.message.answer("❌ Purchase canceled.")

# ================= SHOW SERVICES =================
@dp.callback_query(lambda c: c.data == "services")
async def show_services(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (call.from_user.id,))
    lang = cur.fetchone()[0]
    conn.close()
    await call.message.edit_text(
        "Choose service" if lang=="en" else "اختر الخدمة",
        reply_markup=services_keyboard()
    )

# ================= RUN =====================
async def main():
    print("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
