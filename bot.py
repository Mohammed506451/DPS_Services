from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import sqlite3

# --- Telegram Bot Token ---
TOKEN = "6872510077:AAFtVniM9OJRPDkjozI8hU52AvoDZ7njtsI"

# --- Admin usernames ---
ADMINS = ["MD18073"]  # Add more usernames here

# --- Database ---
conn = sqlite3.connect('botdata.db', check_same_thread=False)
cursor = conn.cursor()

# Users table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance REAL DEFAULT 0,
    language TEXT
)
''')

# Products table
cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price REAL
)
''')

# Top-up requests table
cursor.execute('''
CREATE TABLE IF NOT EXISTS topup_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    amount REAL,
    status TEXT DEFAULT 'pending'
)
''')
conn.commit()

# --- Start command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "NoUsername"
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)", (user_id, username))
    conn.commit()

    keyboard = [
        [InlineKeyboardButton("🇱🇧 العربية", callback_data='lang_ar')],
        [InlineKeyboardButton("🇺🇸 English", callback_data='lang_en')]
    ]
    await update.message.reply_text("🌐 Please choose your language / الرجاء اختيار اللغة:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Build main menu ---
def build_main_menu(lang, is_admin):
    buttons = [
        [InlineKeyboardButton("الرصيد 💰" if lang=='ar' else "Balance 💰", callback_data='balance')],
        [InlineKeyboardButton("المنتجات 🛒" if lang=='ar' else "Products 🛒", callback_data='products')],
        [InlineKeyboardButton("شحن الرصيد 💵" if lang=='ar' else "Top-up Request 💵", callback_data='topup_request')],
        [InlineKeyboardButton("اللغة 🌐" if lang=='ar' else "Language 🌐", callback_data='language')]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton("🔧 لوحة الإدارة" if lang=='ar' else "Admin Panel 🔧", callback_data='admin')])
    return InlineKeyboardMarkup(buttons)

# --- Build admin panel ---
def build_admin_panel(lang):
    buttons = [
        [InlineKeyboardButton("Add Product / إضافة خدمة", callback_data='admin_addproduct')],
        [InlineKeyboardButton("Top-up Requests / طلبات شحن الرصيد", callback_data='admin_topup_requests')],
        [InlineKeyboardButton("View Users / أرصدة المستخدمين", callback_data='admin_users')],
        [InlineKeyboardButton("Back / رجوع", callback_data='back')]
    ]
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
    is_admin = username.lower() in [a.lower() for a in ADMINS]

    # --- Language selection ---
    if query.data.startswith("lang_"):
        lang = 'en' if query.data=='lang_en' else 'ar'
        cursor.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
        conn.commit()
        await query.edit_message_text("اختر من القائمة:" if lang=='ar' else "Please choose:", reply_markup=build_main_menu(lang, is_admin))
        return

    # --- User commands ---
    if query.data == 'balance':
        await query.edit_message_text(f"رصيدك الحالي: ${balance:.2f}" if lang=='ar' else f"Your balance: ${balance:.2f}")
    elif query.data == 'products':
        cursor.execute("SELECT id, name, price FROM products")
        products = cursor.fetchall()
        if not products:
            await query.edit_message_text("⚠ No products yet" if lang=='en' else "⚠ لا توجد منتجات")
            return
        keyboard = [[InlineKeyboardButton(f"{p[1]} - ${p[2]:.2f}", callback_data=f"buy_{p[0]}")] for p in products]
        keyboard.append([InlineKeyboardButton("Back / رجوع", callback_data='back')])
        await query.edit_message_text("Products:" if lang=='en' else "المنتجات:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data.startswith("buy_"):
        pid = int(query.data.split("_")[1])
        cursor.execute("SELECT name, price FROM products WHERE id=?", (pid,))
        product = cursor.fetchone()
        if product:
            name, price = product
            if balance >= price:
                balance -= price
                cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (balance, user_id))
                conn.commit()
                await query.edit_message_text(f"✅ Purchased {name} for ${price:.2f}" if lang=='en' else f"✅ تم شراء {name} مقابل ${price:.2f}")
            else:
                await query.edit_message_text("❌ Not enough balance" if lang=='en' else "❌ الرصيد غير كاف")
        await query.edit_message_text("اختر من القائمة:" if lang=='ar' else "Please choose:", reply_markup=build_main_menu(lang, is_admin))
    elif query.data == 'language':
        keyboard = [
            [InlineKeyboardButton("🇱🇧 العربية", callback_data='lang_ar')],
            [InlineKeyboardButton("🇺🇸 English", callback_data='lang_en')]
        ]
        await query.edit_message_text("🌐 اختر اللغة / Choose language:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == 'topup_request':
        await query.edit_message_text("⚠ Send /requesttopup <amount> to request top-up" if lang=='en' else "⚠ ارسل /requesttopup <المبلغ> لطلب شحن الرصيد")

    # --- Admin panel ---
    elif query.data == 'admin' and is_admin:
        await query.edit_message_text("🔧 Admin Panel / لوحة الإدارة", reply_markup=build_admin_panel(lang))
    elif query.data == 'admin_addproduct' and is_admin:
        await query.edit_message_text("⚠ Send /addproduct <name> <price>" if lang=='en' else "⚠ ارسل /addproduct <اسم> <السعر>")
    elif query.data == 'admin_topup_requests' and is_admin:
        cursor.execute("SELECT id, username, amount, status FROM topup_requests WHERE status='pending'")
        requests = cursor.fetchall()
        if not requests:
            await query.edit_message_text("No pending requests" if lang=='en' else "لا توجد طلبات شحن")
            return
        text = "\n".join([f"ID:{r[0]} {r[1]} - ${r[2]:.2f}" for r in requests])
        await query.edit_message_text(text)
    elif query.data == 'admin_users' and is_admin:
        cursor.execute("SELECT username, balance FROM users")
        users = cursor.fetchall()
        text = "\n".join([f"{u[0]}: ${u[1]:.2f}" for u in users])
        await query.edit_message_text("Users:\n"+text if lang=='en' else "المستخدمون:\n"+text)
    elif query.data == 'back':
        await query.edit_message_text("اختر من القائمة:" if lang=='ar' else "Please choose:", reply_markup=build_main_menu(lang, is_admin))

# --- User top-up request command ---
async def request_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "NoUsername"
    args = context.args
    if len(args) != 1:
        await update.message.reply_text("Usage: /requesttopup <amount>")
        return
    try:
        amount = float(args[0])
    except:
        await update.message.reply_text("Amount must be a number")
        return
    cursor.execute("INSERT INTO topup_requests (user_id, username, amount) VALUES (?, ?, ?)", (user_id, username, amount))
    conn.commit()
    await update.message.reply_text(f"✅ Top-up request of ${amount:.2f} sent. Admin will approve soon.")

# --- Admin commands (add product / topup user) ---
async def topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.from_user.username or ""
    if username.lower() not in [a.lower() for a in ADMINS]:
        await update.message.reply_text("❌ You are not admin")
        return
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Usage: /topup <username> <amount>")
        return
    target_user, amount = args
    try:
        amount = float(amount)
    except:
        await update.message.reply_text("Amount must be a number")
        return
    cursor.execute("UPDATE users SET balance = balance + ? WHERE username=?", (amount, target_user))
    conn.commit()
    await update.message.reply_text(f"✅ {amount} added to {target_user}")

async def addproduct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.from_user.username or ""
    if username.lower() not in [a.lower() for a in ADMINS]:
        await update.message.reply_text("❌ You are not admin")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /addproduct <name> <price>")
        return
    name = " ".join(args[:-1])
    try:
        price = float(args[-1])
    except:
        await update.message.reply_text("Price must be a number")
        return
    cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", (name, price))
    conn.commit()
    await update.message.reply_text(f"✅ Product {name} added for ${price:.2f}")

# --- Run bot ---
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("requesttopup", request_topup))
app.add_handler(CommandHandler("topup", topup))
app.add_handler(CommandHandler("addproduct", addproduct))
app.add_handler(CallbackQueryHandler(button))
app.run_polling()
