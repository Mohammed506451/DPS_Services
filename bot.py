import psycopg2
from psycopg2.extras import RealDictCursor
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

API_TOKEN = "6872510077:AAFtVniM9OJRPDkjozI8hU52AvoDZ7njtsI"
ADMIN_USERNAME = "MD18073"
DATABASE_URL = "postgresql://postgres:wTWqoVJnKEDRtDDWFlpJNfSGGRdYCJHB@nozomi.proxy.rlwy.net:22169/railway"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🇱🇧 Arabic", callback_data="lang_ar"),
        InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")
    )
    await message.reply("Choose your language / اختر لغتك", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith("lang_"))
async def choose_language(callback_query: types.CallbackQuery):
    lang = callback_query.data.split("_")[1]
    keyboard = InlineKeyboardMarkup()
    if callback_query.from_user.username == ADMIN_USERNAME:
        keyboard.add(InlineKeyboardButton("Admin Panel", callback_data="admin_panel"))
    keyboard.add(InlineKeyboardButton("Show Services", callback_data="show_services"))
    await bot.send_message(callback_query.from_user.id, "Main menu:", reply_markup=keyboard)
    await callback_query.answer()

def get_services_keyboard():
    db = get_db()
    cur = db.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS products (id SERIAL PRIMARY KEY, name TEXT, price REAL);")
    cur.execute("SELECT * FROM products")
    rows = cur.fetchall()
    db.close()
    buttons = []
    for r in rows:
        buttons.append([InlineKeyboardButton(f"{r['name']} - ${r['price']}", callback_data=f"buy_{r['id']}")])
    return InlineKeyboardMarkup(buttons)

@dp.callback_query_handler(lambda c: c.data == "show_services")
async def show_services(callback_query: types.CallbackQuery):
    keyboard = get_services_keyboard()
    if not keyboard.inline_keyboard:
        await bot.send_message(callback_query.from_user.id, "No services available currently.")
    else:
        await bot.send_message(callback_query.from_user.id, "Choose a service:", reply_markup=keyboard)
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def buy_service(callback_query: types.CallbackQuery):
    service_id = int(callback_query.data.split("_")[1])
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM products WHERE id=%s", (service_id,))
    service = cur.fetchone()
    db.close()
    if service:
        await bot.send_message(callback_query.from_user.id, f"You selected: {service['name']} - ${service['price']}")
    else:
        await bot.send_message(callback_query.from_user.id, "Service not found.")
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_panel")
async def admin_panel(callback_query: types.CallbackQuery):
    if callback_query.from_user.username == ADMIN_USERNAME:
        await bot.send_message(callback_query.from_user.id, "Admin panel coming soon!")
    else:
        await bot.send_message(callback_query.from_user.id, "❌ You are not an admin.")
    await callback_query.answer()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
