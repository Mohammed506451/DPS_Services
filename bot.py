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
        category TEXT,
        subcategory TEXT,
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
            [InlineKeyboardButton(text="💰 الرصيد", callback_data="balance")]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Services", callback_data="services")],
            [InlineKeyboardButton(text="💰 Balance", callback_data="balance")]
        ])

def service_categories_keyboard(lang):
    if lang=="ar":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="PayPal Services", callback_data="cat_paypal")],
            [InlineKeyboardButton(text="SSN Services", callback_data="cat_ssn")],
            [InlineKeyboardButton(text="Visa Card", callback_data="cat_visa")],
            [InlineKeyboardButton(text="Email", callback_data="cat_email")],
            [InlineKeyboardButton(text="⬅️ رجوع", callback_data="back")]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="PayPal Services", callback_data="cat_paypal")],
            [InlineKeyboardButton(text="SSN Services", callback_data="cat_ssn")],
            [InlineKeyboardButton(text="Visa Card", callback_data="cat_visa")],
            [InlineKeyboardButton(text="Email", callback_data="cat_email")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="back")]
        ])

def service_subcategory_keyboard(category, lang):
    buttons = []
    if category=="cat_paypal":
        if lang=="en":
            buttons = [
                [InlineKeyboardButton("USA PayPal", callback_data="sub_us")],
                [InlineKeyboardButton("UK PayPal", callback_data="sub_uk")],
                [InlineKeyboardButton("Canada PayPal", callback_data="sub_ca")],
            ]
        else:
            buttons = [
                [InlineKeyboardButton("USA PayPal", callback_data="sub_us")],
                [InlineKeyboardButton("UK PayPal", callback_data="sub_uk")],
                [InlineKeyboardButton("Canada PayPal", callback_data="sub_ca")],
            ]
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="services")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def service_items_keyboard(subcategory, lang):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price FROM services WHERE subcategory=%s ORDER BY id", (subcategory,))
    items = cur.fetchall()
    conn.close()
    buttons = [[InlineKeyboardButton(f"{i[1]} - ${i[2]}", callback_data=f"buy_{i[0]}")] for i in items]
    back_text = "⬅️ Back" if lang=="en" else "⬅️ رجوع"
    buttons.append([InlineKeyboardButton(back_text, callback_data="cat_paypal")])
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
@dp.callback_query(lambda c: c.data=="services")
async def show_service_categories(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (call.from_user.id,))
    lang = cur.fetchone()[0]
    conn.close()
    await call.message.edit_text("Select Category" if lang=="en" else "اختر التصنيف", reply_markup=service_categories_keyboard(lang))

# ================= SERVICE SUBCATEGORY =================
@dp.callback_query(lambda c: c.data.startswith("cat_"))
async def show_subcategory(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (call.from_user.id,))
    lang = cur.fetchone()[0]
    conn.close()
    await call.message.edit_text("Select Subcategory" if lang=="en" else "اختر التصنيف الفرعي", reply_markup=service_subcategory_keyboard(call.data, lang))

# ================= SERVICE ITEMS =================
@dp.callback_query(lambda c: c.data.startswith("sub_"))
async def show_items(call: types.CallbackQuery):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE user_id=%s", (call.from_user.id,))
    lang = cur.fetchone()[0]
    conn.close()
    await call.message.edit_text("Select Item" if lang=="en" else "اختر المنتج", reply_markup=service_items_keyboard(call.data, lang))

# ================= PURCHASE CONFIRMATION =================
@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def confirm_purchase(call: types.CallbackQuery):
    item_id = int(call.data.split("_")[1])
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, price FROM services WHERE id=%s", (item_id,))
    item = cur.fetchone()
    cur.execute("SELECT balance FROM users WHERE user_id=%s", (call.from_user.id,))
    balance = cur.fetchone()[0]
    conn.close()

    if balance < item[1]:
        await call.message.answer(f"❌ Not enough balance. Your balance: ${balance}")
        return

    # Confirmation buttons
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Confirm ✅", callback_data=f"pay_{item_id}")],
        [InlineKeyboardButton(text="Cancel ❌", callback_data="back")]
    ])
    await call.message.answer(f"💰 You are buying {item[0]} for ${item[1]}", reply_markup=kb)

# ================= FINALIZE PURCHASE =================
@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def finalize_purchase(call: types.CallbackQuery):
    item_id = int(call.data.split("_")[1])
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, price FROM services WHERE id=%s", (item_id,))
    item = cur.fetchone()
    cur.execute("SELECT balance FROM users WHERE user_id=%s", (call.from_user.id,))
    balance = cur.fetchone()[0]

    new_balance = balance - item[1]
    cur.execute("UPDATE users SET balance=%s WHERE user_id=%s", (new_balance, call.from_user.id))
    conn.commit()
    conn.close()

    await call.message.answer(f"✅ Purchase successful! New balance: ${new_balance}")

# ================= BALANCE / TOPUP ====================
@dp.callback_query(lambda c: c.data=="balance")
async def topup_menu(call: types.CallbackQuery):
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

# ================= BACK BUTTON =================
@dp.callback_query(lambda c: c.data=="back")
async def go_back(call: types.CallbackQuery):
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
