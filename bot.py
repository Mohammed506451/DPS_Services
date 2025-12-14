import asyncio
import os
import psycopg2
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

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
        total_added NUMERIC DEFAULT 0,
        total_spent NUMERIC DEFAULT 0,
        lang TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id SERIAL PRIMARY KEY,
        name TEXT,
        price NUMERIC
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS topups (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        amount NUMERIC,
        method TEXT,
        status TEXT DEFAULT 'pending'
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= HELPERS =================
async def check_subscription(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except TelegramBadRequest:
        return False

def join_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
        [InlineKeyboardButton(text="🔄 Check", callback_data="check_join")]
    ])

def lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇱🇧 العربية", callback_data="lang_ar")],
        [InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_en")]
    ])

def main_menu(lang):
    text = "🛒 Services" if lang == "en" else "🛒 الخدمات"
    bal = "💰 Balance" if lang == "en" else "💰 الرصيد"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data="services")],
        [InlineKeyboardButton(text=bal, callback_data="balance")]
    ])

def back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅ Back", callback_data="back")]
    ])

# ================= START ====================
@dp.message(CommandStart())
async def start(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await message.answer(
            "🔒 Please join our channel first",
            reply_markup=join_keyboard()
        )
        return

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (user_id)
        VALUES (%s)
        ON CONFLICT (user_id) DO NOTHING
    """, (message.from_user.id,))
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (message.from_user.id,))
    lang = cur.fetchone()[0]
    conn.commit()
    conn.close()

    if lang:
        await message.answer("Main Menu", reply_markup=main_menu(lang))
    else:
        await message.answer("Choose language / اختر اللغة", reply_markup=lang_keyboard())

# ================= JOIN CHECK ==============
@dp.callback_query(lambda c: c.data == "check_join")
async def recheck(call: types.CallbackQuery):
    if await check_subscription(call.from_user.id):
        await start(call.message)
    else:
        await call.answer("❌ You must join first", show_alert=True)

# ================= LANGUAGE =================
@dp.callback_query(lambda c: c.data.startswith("lang_"))
async def set_lang(call: types.CallbackQuery):
    lang = call.data.split("_")[1]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET lang=%s WHERE user_id=%s", (lang, call.from_user.id))
    conn.commit()
    conn.close()

    await call.message.edit_text("Main Menu", reply_markup=main_menu(lang))

# ================= SERVICES =================
@dp.callback_query(lambda c: c.data == "services")
async def services(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, price FROM services")
    data = cur.fetchall()
    conn.close()

    if not data:
        await call.message.edit_text("No services available", reply_markup=back_button())
        return

    kb = []
    for name, price in data:
        kb.append([InlineKeyboardButton(text=f"{name} — ${price}", callback_data=f"buy_{name}")])
    kb.append([InlineKeyboardButton(text="⬅ Back", callback_data="back")])

    await call.message.edit_text("🛒 Services", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

# ================= BUY =====================
@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy(call: types.CallbackQuery):
    service = call.data.replace("buy_", "")
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT price FROM services WHERE name=%s", (service,))
    price = cur.fetchone()[0]

    cur.execute("SELECT balance FROM users WHERE user_id=%s", (call.from_user.id,))
    balance = cur.fetchone()[0]

    if balance < price:
        await call.answer("❌ Not enough balance", show_alert=True)
        return

    cur.execute("""
        UPDATE users
        SET balance = balance - %s,
            total_spent = total_spent + %s
        WHERE user_id=%s
    """, (price, price, call.from_user.id))

    conn.commit()
    conn.close()

    await call.message.edit_text("✅ Purchase successful", reply_markup=back_button())

# ================= BALANCE =================
@dp.callback_query(lambda c: c.data == "balance")
async def balance(call: types.CallbackQuery):
    await call.message.edit_text(
        "💳 Choose payment method",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Binance", callback_data="pay_Binance")],
            [InlineKeyboardButton(text="CoinEX", callback_data="pay_CoinEX")],
            [InlineKeyboardButton(text="Crypto", callback_data="pay_Crypto")],
            [InlineKeyboardButton(text="⬅ Back", callback_data="back")]
        ])
    )

@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def pay(call: types.CallbackQuery):
    method = call.data.replace("pay_", "")
    await call.message.edit_text(
        f"Send amount for {method}",
        reply_markup=back_button()
    )

@dp.message(lambda m: m.text and m.text.isdigit())
async def topup(message: types.Message):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO topups (user_id, amount, method) VALUES (%s, %s, 'manual')",
        (message.from_user.id, int(message.text))
    )
    conn.commit()
    conn.close()

    await message.answer("✅ Top-up request sent")

# ================= BACK ====================
@dp.callback_query(lambda c: c.data == "back")
async def back(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (call.from_user.id,))
    lang = cur.fetchone()[0]
    conn.close()

    await call.message.edit_text("Main Menu", reply_markup=main_menu(lang))

# ================= RUN =====================
async def main():
    print("BOT RUNNING")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
