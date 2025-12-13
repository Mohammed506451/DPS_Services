from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import sqlite3

# --- Telegram Bot Token ---
TOKEN = "6872510077:AAFtVniM9OJRPDkjozI8hU52AvoDZ7njtsI"

# --- Admin username ---
ADMIN_USERNAME = "MD18073"

# --- Database ---
conn = sqlite3.connect('botdata.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance REAL DEFAULT 0,
    language TEXT
)
''')
conn.commit()

# --- Start command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "NoUsername"
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)", (user_id, username))
    conn.commit()

    # Language selection buttons
    keyboard = [
        [InlineKeyboardButton("🇱🇧 العربية", callback_data='lang_ar')],
        [InlineKeyboardButton("🇺🇸 English", callback_data='lang_en')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🌐 Please choose your language / الرجاء اختيار اللغة:", reply_markup=reply_markup)

# --- Build main menu ---
def build_main_menu(lang, is_admin):
    buttons = [
        [InlineKeyboardButton("الرصيد 💰" if lang=='ar' else "Balance 💰", callback_data='balance')],
        [InlineKeyboardButton("المنتجات 🛒" if lang=='ar' else "Products 🛒", callback_data='products')],
        [InlineKeyboardButton("اللغة 🌐" if lang=='ar' else "Language 🌐", callback_data='language')]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton("🔧 لوحة الإدارة" if lang=='ar' else "Admin Panel 🔧", callback_data='admin')])
    return InlineKeyboardMarkup(buttons)

# --- Button handler ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    cursor.execute("SELECT username, language, balance FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    if result:
        username, lang, balance = result
    else:
        lang = 'en'
        balance = 0
        username = "NoUsername"

    is_admin = username.lower() == ADMIN_USERNAME.lower()

    # Language selection
    if query.data.startswith("lang_"):
        lang = 'en' if query.data=='lang_en' else 'ar'
        cursor.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
        conn.commit()
        await query.edit_message_text("اختر من القائمة:" if lang=='ar' else "Please choose:", reply_markup=build_main_menu(lang, is_admin))
        return

    # User commands
    if query.data == 'balance':
        await query.edit_message_text(f"رصيدك الحالي: ${balance:.2f}" if lang=='ar' else f"Your balance: ${balance:.2f}")
    elif query.data == 'products':
        await query.edit_message_text("⚠ Placeholder for products" if lang=='en' else "⚠ مكان المنتجات")
    elif query.data == 'language':
        await query.edit_message_text("🌐 اختر اللغة / Choose language:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇱🇧 العربية", callback_data='lang_ar')],
            [InlineKeyboardButton("🇺🇸 English", callback_data='lang_en')]
        ]))

    # Admin panel
    elif query.data == 'admin' and is_admin:
        keyboard = [
            [InlineKeyboardButton("Add Product / إضافة خدمة", callback_data='admin_addproduct')],
            [InlineKeyboardButton("Top-up User / شحن الرصيد", callback_data='admin_topup')],
            [InlineKeyboardButton("View Users / أرصدة المستخدمين", callback_data='admin_users')]
        ]
        await query.edit_message_text("🔧 Admin Panel / لوحة الإدارة", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Run bot ---
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.run_polling()
