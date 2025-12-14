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
    cur.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        price NUMERIC NOT NULL
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ================= SUBSCRIPTION CHECK =================
async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status != "left"
    except:
        return False

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

def services_keyboard(lang, services):
    buttons = []
    for s in services:
        buttons.append([InlineKeyboardButton(text=f"{s[0]} — ${s[1]}", callback_data=f"buy_{s[0]}")])
    back_text = "⬅️ Back" if lang=="en" else "⬅️ رجوع"
    buttons.append([InlineKeyboardButton(text=back_text, callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def payment_methods_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Binance", callback_data="pay_binance")],
        [InlineKeyboardButton(text="CoinEX", callback_data="pay_coinex")],
        [InlineKeyboardButton(text="Crypto", callback_data="pay_crypto")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
    ])

# ================= START ====================
@dp.message(CommandStart())
async def start(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        await message.answer(f"🔔 Please join our channel first: {CHANNEL_USERNAME}")
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
async def set_language(call: types.CallbackQuery):
    lang = call.data.split("_")[1]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET lang=%s WHERE user_id=%s", (lang, call.from_user.id))
    conn.commit()
    conn.close()
    await call.message.edit_text("Main Menu" if lang=="en" else "القائمة الرئيسية", reply_markup=main_menu(lang))

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
        await call.message.answer("No services available")
        return

    await call.message.edit_text("🛒 Services:" if lang=="en" else "🛒 الخدمات:", reply_markup=services_keyboard(lang, services))

# ================= BACK BUTTON =================
@dp.callback_query(lambda c: c.data=="back")
async def go_back(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (call.from_user.id,))
    lang = cur.fetchone()[0]
    conn.close()
    await call.message.edit_text("Main Menu" if lang=="en" else "القائمة الرئيسية", reply_markup=main_menu(lang))

# ================= TOPUP ====================
@dp.callback_query(lambda c: c.data=="topup")
async def topup(call: types.CallbackQuery):
    await call.message.edit_text("Select payment method:", reply_markup=payment_methods_keyboard())

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
