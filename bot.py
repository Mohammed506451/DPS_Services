import asyncio
import os
import psycopg2
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ================= CONFIG =================
BOT_TOKEN = "6872510077:AAFtVniM9OJRPDkjozI8hU52AvoDZ7njtsI"
ADMIN_USERNAME = "MD18073"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:wTWqoVJnKEDRtDDWFlpJNfSGGRdYCJHB@nozomi.proxy.rlwy.net:22169/railway"
)

CHANNEL_USERNAME = "@Offerwallproxy"  # Users must join this channel

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
        lang TEXT,
        balance NUMERIC DEFAULT 0
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
            [InlineKeyboardButton(text="💰 الرصيد", callback_data="balance")]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Services", callback_data="services")],
            [InlineKeyboardButton(text="💰 Balance", callback_data="balance")]
        ])

def back_button(lang):
    if lang == "ar":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 العودة", callback_data="back")]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back", callback_data="back")]
        ])

# ================= START ====================
@dp.message(CommandStart())
async def start(message: types.Message):
    # check subscription
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
        # user already has language
        lang = row[0]
        await message.answer("Main Menu" if lang == "en" else "القائمة الرئيسية", reply_markup=main_menu(lang))
    else:
        await message.answer("Choose language / اختر اللغة", reply_markup=lang_keyboard())

# ================= LANGUAGE =================
@dp.callback_query(lambda c: c.data.startswith("lang_"))
async def set_language(call: CallbackQuery):
    lang = call.data.split("_")[1]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET lang=%s WHERE user_id=%s", (lang, call.from_user.id))
    conn.commit()
    conn.close()
    await call.message.edit_text("Main Menu" if lang == "en" else "القائمة الرئيسية", reply_markup=main_menu(lang))

# ================= SERVICES =================
@dp.callback_query(lambda c: c.data == "services")
async def show_services(call: CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lang, balance FROM users WHERE user_id=%s", (call.from_user.id,))
    lang, balance = cur.fetchone()
    cur.execute("SELECT DISTINCT category FROM products ORDER BY id")
    categories = cur.fetchall()
    conn.close()

    if not categories:
        await call.message.answer("No services available" if lang == "en" else "لا توجد خدمات")
        return

    kb = InlineKeyboardMarkup()
    for c in categories:
        kb.add(InlineKeyboardButton(text=c[0], callback_data=f"cat_{c[0]}"))
    kb.add(InlineKeyboardButton(text="🔙 Back" if lang=="en" else "🔙 العودة", callback_data="back"))
    await call.message.edit_text("Choose service:" if lang=="en" else "اختر الخدمة:", reply_markup=kb)

# ================= CATEGORY -> PRODUCTS =================
@dp.callback_query(lambda c: c.data.startswith("cat_"))
async def show_products(call: CallbackQuery):
    category = call.data.split("_")[1]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (call.from_user.id,))
    lang = cur.fetchone()[0]
    cur.execute("SELECT id, name, price FROM products WHERE category=%s", (category,))
    products = cur.fetchall()
    conn.close()

    if not products:
        await call.message.answer("No products" if lang=="en" else "لا توجد منتجات")
        return

    kb = InlineKeyboardMarkup()
    for p in products:
        kb.add(InlineKeyboardButton(text=f"{p[1]} — ${p[2]}", callback_data=f"buy_{p[0]}"))
    kb.add(InlineKeyboardButton(text="🔙 Back" if lang=="en" else "🔙 العودة", callback_data="services"))
    await call.message.edit_text("Select product:" if lang=="en" else "اختر المنتج:", reply_markup=kb)

# ================= BUY PRODUCT =================
@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy_product(call: CallbackQuery):
    product_id = int(call.data.split("_")[1])
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, price, message FROM products WHERE id=%s", (product_id,))
    product = cur.fetchone()
    cur.execute("SELECT balance FROM users WHERE user_id=%s", (call.from_user.id,))
    balance = cur.fetchone()[0]

    name, price, message_text = product
    lang = "en"  # default
    if balance >= price:
        cur.execute("UPDATE users SET balance=balance-%s, total_spent=total_spent+%s WHERE user_id=%s",
                    (price, price, call.from_user.id))
        conn.commit()
        await call.message.answer(f"✅ {name} purchased for ${price}\nMessage:\n{message_text}")
    else:
        await call.message.answer("❌ Not enough balance" if lang=="en" else "رصيد غير كافٍ")
    conn.close()

# ================= BALANCE / TOPUP =================
@dp.callback_query(lambda c: c.data == "balance")
async def balance_menu(call: CallbackQuery):
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
async def topup_method(call: CallbackQuery):
    method = call.data.split("_")[1]
    await call.message.answer(f"Send amount to top-up via {method}:")

@dp.message(lambda m: m.text.isdigit())
async def create_topup(message: types.Message):
    amount = int(message.text)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO topups (user_id, amount, method) VALUES (%s,%s,%s)",
                (message.from_user.id, amount, "Unknown"))
    conn.commit()
    conn.close()
    await message.answer("✅ Top-up request sent. Wait for admin approval.")

# ================= BACK BUTTON =================
@dp.callback_query(lambda c: c.data == "back")
async def go_back(call: CallbackQuery):
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
