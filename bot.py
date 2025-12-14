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
        method TEXT,
        status TEXT DEFAULT 'pending'
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= HELPERS =================
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def main_menu(lang):
    if lang == "ar":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 الخدمات", callback_data="services")],
            [InlineKeyboardButton(text="💰 الرصيد", callback_data="balance")]
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Services", callback_data="services")],
        [InlineKeyboardButton(text="💰 Balance", callback_data="balance")]
    ])

def back_button(lang):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔙 رجوع" if lang == "ar" else "🔙 Back",
            callback_data="back"
        )]
    ])

def payment_methods():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Binance", callback_data="pay_Binance")],
        [InlineKeyboardButton(text="CoinEX", callback_data="pay_CoinEX")],
        [InlineKeyboardButton(text="Crypto", callback_data="pay_Crypto")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back")]
    ])

# ================= START ====================
@dp.message(CommandStart())
async def start(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        await message.answer(
            f"🔒 You must subscribe first:\n{CHANNEL_USERNAME}"
        )
        return

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
        (message.from_user.id,)
    )
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (message.from_user.id,))
    row = cur.fetchone()
    conn.close()

    if row and row[0]:
        await message.answer("Main Menu", reply_markup=main_menu(row[0]))
    else:
        await message.answer(
            "Choose language / اختر اللغة",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🇸🇦 العربية", callback_data="lang_ar")],
                [InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_en")]
            ])
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

# ================= SERVICES =================
@dp.callback_query(lambda c: c.data == "services")
async def services(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (call.from_user.id,))
    lang = cur.fetchone()[0]

    cur.execute("SELECT id, name, price FROM services ORDER BY id")
    services = cur.fetchall()
    conn.close()

    if not services:
        await call.message.answer("No services available", reply_markup=back_button(lang))
        return

    keyboard = []
    for s in services:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{s[1]} - ${s[2]}",
                callback_data=f"buy_{s[0]}"
            )
        ])
    keyboard.append([InlineKeyboardButton(
        text="🔙 Back" if lang == "en" else "🔙 رجوع",
        callback_data="back"
    )])

    await call.message.answer(
        "Choose service:" if lang == "en" else "اختر خدمة:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

# ================= BUY =====================
@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy_service(call: types.CallbackQuery):
    service_id = int(call.data.split("_")[1])

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT price FROM services WHERE id=%s", (service_id,))
    price = cur.fetchone()[0]

    cur.execute("SELECT balance, lang FROM users WHERE user_id=%s", (call.from_user.id,))
    balance, lang = cur.fetchone()

    if balance < price:
        await call.message.answer("❌ Not enough balance")
        conn.close()
        return

    cur.execute(
        "UPDATE users SET balance = balance - %s WHERE user_id=%s",
        (price, call.from_user.id)
    )
    conn.commit()
    conn.close()

    await call.message.answer("✅ Purchase successful")

# ================= BALANCE =================
@dp.callback_query(lambda c: c.data == "balance")
async def balance(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT balance FROM users WHERE user_id=%s", (call.from_user.id,))
    bal = cur.fetchone()[0]
    conn.close()

    await call.message.answer(
        f"💰 Balance: ${bal}\nChoose payment method:",
        reply_markup=payment_methods()
    )

# ================= TOPUP ===================
@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def choose_payment(call: types.CallbackQuery):
    method = call.data.split("_")[1]
    await call.message.answer(
        f"Send amount for {method} top-up (numbers only)"
    )
    dp.message.register(lambda m: handle_topup(m, method))

async def handle_topup(message: types.Message, method: str):
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

    await message.answer("✅ Top-up request sent. Admin will review.")

# ================= BACK ====================
@dp.callback_query(lambda c: c.data == "back")
async def back(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (call.from_user.id,))
    lang = cur.fetchone()[0]
    conn.close()

    await call.message.answer("Main Menu", reply_markup=main_menu(lang))

# ================= RUN =====================
async def main():
    print("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
