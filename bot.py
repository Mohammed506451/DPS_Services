import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# -- Configuration --
TOKEN = os.getenv("TG_BOT_TOKEN", "6872510077:AAFtVniM9OJRPDkjozI8hU52AvoDZ7njtsI")
REQUIRED_CHANNEL = "@Offerwallproxy"
ADMIN_USERNAME = "MD18073"  # admin username (no @). You can keep using this check.

# -- Database (simple sqlite) --
conn = sqlite3.connect("botdata.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance REAL DEFAULT 0,
    language TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    name TEXT,
    price REAL
)
""")
conn.commit()

# -- Temporary admin action storage --
# admin_data will store the current admin action and (optionally) auxiliary fields.
admin_data = {}

# -- Helpers --
async def is_subscribed(user_id: int, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        mem = await ctx.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return mem.status not in ("left", "kicked")
    except Exception:
        return False

def join_keyboard():
    url = f"https://t.me/{REQUIRED_CHANNEL.lstrip('@')}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Join Channel", url=url)],
        [InlineKeyboardButton("✅ I Joined", callback_data="check_sub")]
    ])

def language_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇱🇧 العربية", callback_data="lang_ar")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
    ])

def main_menu_kb(lang: str, is_admin: bool):
    txt_services = "الخدمات" if lang == "ar" else "Services"
    txt_topup = "شحن رصيدك" if lang == "ar" else "Top-up your balance"
    txt_contact = "التواصل مع الأدمن" if lang == "ar" else "Contact admin"
    kb = [
        [InlineKeyboardButton(txt_services, callback_data="menu_services")],
        [InlineKeyboardButton(txt_topup, callback_data="menu_topup")],
        [InlineKeyboardButton(txt_contact, callback_data="menu_contact")]
    ]
    if is_admin:
        kb.append([InlineKeyboardButton("🔧 Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(kb)

def admin_panel_kb(lang: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Add Service / إضافة خدمة", callback_data="admin_add_service")],
        [InlineKeyboardButton("Manage Balances / إدارة الأرصدة", callback_data="admin_manage_balances")],
        [InlineKeyboardButton("List Users / قائمة المستخدمين", callback_data="admin_list_users")],
        [InlineKeyboardButton("Back / العودة", callback_data="back_main")]
    ])

# -- Handlers --
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)", (user.id, user.username or "NoUsername"))
    conn.commit()

    # Enforce subscription first
    if not await is_subscribed(user.id, context):
        await update.message.reply_text(
            "🔒 Please join our channel to use this bot.\nJoin and press 'I Joined'.",
            reply_markup=join_keyboard()
        )
        return

    # Show language selection after /start
    await update.message.reply_text("🌐 Please choose your language / الرجاء اختيار اللغة:", reply_markup=language_keyboard())

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    # handle "I Joined" re-check
    if q.data == "check_sub":
        if await is_subscribed(uid, context):
            await q.edit_message_text("🌐 Please choose your language / الرجاء اختيار اللغة:", reply_markup=language_keyboard())
        else:
            await q.edit_message_text("🔒 You still need to join the channel.", reply_markup=join_keyboard())
        return

    # For any other actions require subscription
    if not await is_subscribed(uid, context):
        await q.edit_message_text("🔒 Please join our channel to use the bot.", reply_markup=join_keyboard())
        return

    # Fetch stored user info (safe fetch)
    cursor.execute("SELECT username, language, balance FROM users WHERE user_id=?", (uid,))
    row = cursor.fetchone()
    if row:
        username, lang, balance = row
    else:
        username, lang, balance = (q.from_user.username or "NoUsername"), "en", 0.0

    is_admin = (username.lower() == ADMIN_USERNAME.lower())

    # Language selection -> save and show main menu
    if q.data.startswith("lang_"):
        lang = "ar" if q.data == "lang_ar" else "en"
        cursor.execute("UPDATE users SET language=? WHERE user_id=?", (lang, uid))
        conn.commit()
        await q.edit_message_text("اختر من القائمة:" if lang == "ar" else "Please choose:", reply_markup=main_menu_kb(lang, is_admin))
        return

    # Main menu options
    if q.data == "menu_services":
        cursor.execute("SELECT category, name, price FROM products ORDER BY category, name")
        products = cursor.fetchall()
        if not products:
            await q.edit_message_text("لا توجد خدمات حاليا" if lang == "ar" else "No services available at the moment",
                                      reply_markup=main_menu_kb(lang, is_admin))
            return
        lines = [f"{name} — ${price:.2f} ({category})" for category, name, price in products]
        text = ("\n".join(lines))
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", callback_data="back_main")]]))
        return

    if q.data == "menu_topup":
        text = ("لشحن رصيدك، تواصل مع الأدمن" if lang == "ar" else "To top up your balance, contact the admin.")
        admin_url = f"https://t.me/{ADMIN_USERNAME}"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Contact Admin", url=admin_url)],
            [InlineKeyboardButton("◀️ Back", callback_data="back_main")]
        ])
        await q.edit_message_text(text, reply_markup=kb)
        return

    if q.data == "menu_contact":
        admin_url = f"https://t.me/{ADMIN_USERNAME}"
        text = ("تواصل مع الأدمن عبر الزر أدناه" if lang == "ar" else "Contact the admin using the button below.")
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Contact Admin", url=admin_url)],
            [InlineKeyboardButton("◀️ Back", callback_data="back_main")]
        ]))
        return

    # Back to main
    if q.data == "back_main":
        await q.edit_message_text("اختر من القائمة:" if lang == "ar" else "Please choose:", reply_markup=main_menu_kb(lang, is_admin))
        return

    # Admin panel entry
    if q.data == "admin_panel" and is_admin:
        await q.edit_message_text("🔧 Admin Panel", reply_markup=admin_panel_kb(lang))
        return

    # Admin actions (require admin)
    if q.data == "admin_add_service" and is_admin:
        admin_data['action'] = 'add_service'
        # instructions: category|name|price
        await q.edit_message_text("Send new service as: category|name|price\nExample: Services|Premium Proxy|2.50")
        return

    if q.data == "admin_manage_balances" and is_admin:
        admin_data['action'] = 'manage_balances'
        await q.edit_message_text("Send in format: topup|username|amount  OR  deduct|username|amount\nExample: topup|someuser|5.0")
        return

    if q.data == "admin_list_users" and is_admin:
        cursor.execute("SELECT username, balance FROM users ORDER BY balance DESC")
        users = cursor.fetchall()
        if not users:
            await q.edit_message_text("No users found.")
            return
        lines = [f"{u} — ${b:.2f}" for u, b in users]
        # limit output length to avoid very long messages
        text = "\n".join(lines[:200])
        await q.edit_message_text("Users and balances:\n" + text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", callback_data="admin_panel")]]))
        return

    # fallback
    await q.edit_message_text("Unsupported action or insufficient permissions.")

# -- Admin text handler: handles add service & manage balances --
async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    uid = user.id
    cursor.execute("SELECT username FROM users WHERE user_id=?", (uid,))
    row = cursor.fetchone()
    username = row[0] if row else (user.username or "NoUsername")
    if username.lower() != ADMIN_USERNAME.lower():
        # not admin -> ignore
        return

    text = update.message.text.strip()
    action = admin_data.get('action')

    if action == 'add_service':
        # Expect: category|name|price
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 3:
            await update.message.reply_text("Invalid format. Send as: category|name|price\nExample: Services|Premium Proxy|2.50")
            return
        category, name, price_s = parts
        try:
            price = float(price_s)
        except ValueError:
            await update.message.reply_text("Invalid price. Use a number like 2.50")
            return
        cursor.execute("INSERT INTO products (category, name, price) VALUES (?,?,?)", (category, name, price))
        conn.commit()
        admin_data.clear()
        await update.message.reply_text(f"Service added: {name} — ${price:.2f} ({category})")
        return

    if action == 'manage_balances':
        # Expect: topup|username|amount  OR  deduct|username|amount
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 3:
            await update.message.reply_text("Invalid format. Send as: topup|username|amount  OR  deduct|username|amount")
            return
        op, target_username, amount_s = parts
        op = op.lower()
        try:
            amount = float(amount_s)
        except ValueError:
            await update.message.reply_text("Invalid amount. Use a number like 5.0")
            return
        # accept username with or without @
        target_username = target_username.lstrip("@")
        cursor.execute("SELECT user_id, balance FROM users WHERE username=?", (target_username,))
        res = cursor.fetchone()
        if not res:
            await update.message.reply_text("User not found in database.")
            return
        target_id, current_balance = res
        if op == "topup":
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, target_id))
            conn.commit()
            await update.message.reply_text(f"Topped up {target_username} by ${amount:.2f}. New balance: ${current_balance + amount:.2f}")
            admin_data.clear()
            return
        elif op == "deduct":
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, target_id))
            conn.commit()
            await update.message.reply_text(f"Deducted ${amount:.2f} from {target_username}. New balance: ${current_balance - amount:.2f}")
            admin_data.clear()
            return
        else:
            await update.message.reply_text("Operation must be 'topup' or 'deduct'.")
            return

    # if no pending admin action, allow simple admin commands in text form as well
    # e.g. addservice category|name|price  OR topup username amount
    lowered = text.lower()
    if lowered.startswith("addservice "):
        payload = text[len("addservice "):].strip()
        parts = [p.strip() for p in payload.split("|")]
        if len(parts) != 3:
            await update.message.reply_text("Invalid format. Send as: addservice category|name|price")
            return
        category, name, price_s = parts
        try:
            price = float(price_s)
        except ValueError:
            await update.message.reply_text("Invalid price. Use a number like 2.50")
            return
        cursor.execute("INSERT INTO products (category, name, price) VALUES (?,?,?)", (category, name, price))
        conn.commit()
        await update.message.reply_text(f"Service added: {name} — ${price:.2f} ({category})")
        return

    if lowered.startswith("topup ") or lowered.startswith("deduct "):
        parts = text.split()
        if len(parts) != 3:
            await update.message.reply_text("Invalid format. Send: topup username amount  OR  deduct username amount")
            return
        op = parts[0].lower()
        target_username = parts[1].lstrip("@")
        try:
            amount = float(parts[2])
        except ValueError:
            await update.message.reply_text("Invalid amount. Use a number like 5.0")
            return
        cursor.execute("SELECT user_id, balance FROM users WHERE username=?", (target_username,))
        res = cursor.fetchone()
        if not res:
            await update.message.reply_text("User not found in database.")
            return
        target_id, current_balance = res
        if op == "topup":
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, target_id)); conn.commit()
            await update.message.reply_text(f"Topped up {target_username} by ${amount:.2f}. New balance: ${current_balance + amount:.2f}")
        else:
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, target_id)); conn.commit()
            await update.message.reply_text(f"Deducted ${amount:.2f} from {target_username}. New balance: ${current_balance - amount:.2f}")
        return

    # No matching admin action
    await update.message.reply_text("No admin action in progress. Use the Admin Panel buttons or send a supported admin command.")

# -- App setup --
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
# Admin text handler (only admin messages processed inside)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_handler))

if __name__ == "__main__":
    print("Bot running. Make sure TG_BOT_TOKEN is set if you prefer env var and bot is member/admin of", REQUIRED_CHANNEL)
    app.run_polling()