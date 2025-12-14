import os
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

API_TOKEN = "6872510077:AAFtVniM9OJRPDkjozI8hU52AvoDZ7njtsI"
ADMIN_USERNAME = "MD18073"  # Without @

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Use the same database as dashboard
DB = os.path.join(os.getcwd(), "botdata.db")

# ===============================
# DATABASE HELPER
# ===============================
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# ===============================
# START / LANGUAGE SELECTION
# ===============================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🇱🇧 Arabic", callback_data="lang_ar"),
        InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")
    )
    await message.reply("Choose your language / اختر لغتك", reply_markup=keyboard)

# ===============================
# CALLBACKS
# ===============================
@dp.callback_query_handler(lambda c: c.data.startswith("lang_"))
async def choose_language(callback_query: types.CallbackQuery):
    lang = callback_query.data.split("_")[1]

    keyboard = InlineKeyboardMarkup()

    # Admin menu
    if message_is_admin(callback_query.from_user.username):
        keyboard.add(
            InlineKeyboardButton("Admin Panel", callback_data="admin_panel")
        )

    # User menu
    keyboard.add(
        InlineKeyboardButton("Show Services", callback_data="show_services")
    )

    await bot.send_message(callback_query.from_user.id, "Main menu:", reply_markup=keyboard)
    await callback_query.answer()

# ===============================
# ADMIN CHECK
# ===============================
def message_is_admin(username):
    return username == ADMIN_USERNAME

# ===============================
# SHOW SERVICES
# ===============================
def get_services_keyboard():
    db = get_db()
    rows = db.execute("SELECT * FROM products").fetchall()
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

# ===============================
# HANDLE BUY SERVICE
# ===============================
@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def buy_service(callback_query: types.CallbackQuery):
    service_id = int(callback_query.data.split("_")[1])
    db = get_db()
    service = db.execute("SELECT * FROM products WHERE id=?", (service_id,)).fetchone()
    db.close()

    if service:
        await bot.send_message(callback_query.from_user.id, f"You selected: {service['name']} - ${service['price']}")
    else:
        await bot.send_message(callback_query.from_user.id, "Service not found.")
    await callback_query.answer()

# ===============================
# ADMIN PANEL PLACEHOLDER
# ===============================
@dp.callback_query_handler(lambda c: c.data == "admin_panel")
async def admin_panel(callback_query: types.CallbackQuery):
    if message_is_admin(callback_query.from_user.username):
        await bot.send_message(callback_query.from_user.id, "Admin panel features coming soon!")
    else:
        await bot.send_message(callback_query.from_user.id, "❌ You are not an admin.")
    await callback_query.answer()

# ===============================
# RUN BOT
# ===============================
if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
