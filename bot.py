import asyncio
import os
import psycopg2
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================
BOT_TOKEN = "6872510077:AAFtVniM9OJRPDkjozI8hU52AvoDZ7njtsI"
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
async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def join_channel_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔔 Join Channel",
            url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"
        )],
        [InlineKeyboardButton(text="✅ I've Joined", callback_data="check_sub")]
    ])

def main_menu(lang):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🛒 Services", callback_data="services")],
        [InlineKeyboardButton("💰 Balance", callback_data="balance")]
    ])

# ================= START =================
@dp.message(CommandStart())
async def start(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        await message.answer(
            "🔒 Please join our channel to use the bot",
            reply_markup=join_channel_button()
        )
        return

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
        (message.from_user.id,)
    )
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (message.from_user.id,))
    lang = cur.fetchone()[0]
    conn.close()

    if lang:
        await message.answer("Main Menu", reply_markup=main_menu(lang))
    else:
        await message.answer(
            "Choose language",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
                [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")]
            ])
        )

@dp.callback_query(lambda c: c.data == "check_sub")
async def check_sub(call: types.CallbackQuery):
    if await is_subscribed(call.from_user.id):
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
    cur.execute("SELECT id, name, price FROM services")
    services = cur.fetchall()
    conn.close()

    if not services:
        await call.message.edit_text("No services available", reply_markup=main_menu("en"))
        return

    keyboard = [
        [InlineKeyboardButton(f"{s[1]} - ${s[2]}", callback_data=f"buy_{s[0]}")]
        for s in services
    ]
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back")])

    await call.message.edit_text("Choose service:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

# ================= BUY =================
@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy(call: types.CallbackQuery):
    sid = int(call.data.split("_")[1])

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT price FROM services WHERE id=%s", (sid,))
    price = cur.fetchone()[0]

    cur.execute("SELECT balance FROM users WHERE user_id=%s", (call.from_user.id,))
    balance = cur.fetchone()[0]

    if balance < price:
        await call.answer("❌ Not enough balance", show_alert=True)
        conn.close()
        return

    cur.execute("""
        UPDATE users 
        SET balance = balance - %s,
            total_spent = total_spent + %s
        WHERE user_id=%s
    """, (price, price, call.from_user.id))

    conn.commit()
    conn.close()

    await call.answer("✅ Purchase successful", show_alert=True)

# ================= BALANCE =================
@dp.callback_query(lambda c: c.data == "balance")
async def balance(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT balance FROM users WHERE user_id=%s", (call.from_user.id,))
    bal = cur.fetchone()[0]
    conn.close()

    await call.message.edit_text(
        f"💰 Balance: ${bal}\nChoose payment method:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("Binance", callback_data="topup_Binance")],
            [InlineKeyboardButton("CoinEX", callback_data="topup_CoinEX")],
            [InlineKeyboardButton("Crypto", callback_data="topup_Crypto")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ])
    )

# ================= TOPUP =================
@dp.callback_query(lambda c: c.data.startswith("topup_"))
async def topup(call: types.CallbackQuery):
    method = call.data.split("_")[1]
    await call.message.edit_text(
        f"Send amount for {method} top-up (numbers only)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ])
    )
    dp.message.register(lambda m: process_topup(m, method))

async def process_topup(message: types.Message, method):
    if not message.text.isdigit():
        return

    amount = int(message.text)

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO topups (user_id, amount, method) VALUES (%s, %s, %s)",
        (message.from_user.id, amount, method)
    )
    conn.commit()
    conn.close()

    await message.answer("✅ Top-up request sent. Await approval.")

# ================= BACK =================
@dp.callback_query(lambda c: c.data == "back")
async def back(call: types.CallbackQuery):
    await call.message.edit_text("Main Menu", reply_markup=main_menu("en"))

# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
