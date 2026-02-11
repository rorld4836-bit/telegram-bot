import os
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = "battlertf"
STATE_FILE = "state.json"

# ================= СОСТОЯНИЕ =================
STATE = {
    "participants": [],
    "posts": {},
    "user_data": {}
}

# ================= БЕЗОПАСНОЕ СОХРАНЕНИЕ =================
def save_state():
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(STATE, f)
    except Exception as e:
        print("Ошибка сохранения:", e)

def load_state():
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            STATE.update(json.load(f))
    except Exception as e:
        print("Ошибка загрузки:", e)

# ================= МЕНЮ =================
def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚔️ Участвовать", callback_data="join"),
            InlineKeyboardButton("📜 Правила", callback_data="rules")
        ],
        [
            InlineKeyboardButton("🔍 Найти себя", callback_data="find_me"),
            InlineKeyboardButton("🔗 Пригласить", callback_data="invite")
        ]
    ])

# ================= /START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid not in STATE["user_data"]:
        STATE["user_data"][uid] = {
            "invites": 0,
            "wins": 0
        }
        save_state()

    await update.message.reply_text(
        "🔥 Добро пожаловать в Битву Ников!\n\n"
        f"Турнир проходит в канале:\n👉 https://t.me/{CHANNEL}\n\n"
        "Используй кнопки ниже 👇",
        reply_markup=main_menu()
    )

# ================= JOIN =================
async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()  # отвечаем сразу

    uid = q.from_user.id

    if uid in STATE["participants"]:
        await q.message.reply_text("Ты уже участвуешь!")
        return

    STATE["participants"].append(uid)
    save_state()

    await q.message.reply_text("✅ Ты успешно добавлен в турнир!")

# ================= FIND ME =================
async def find_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    if uid not in STATE["participants"]:
        await q.message.reply_text("Ты сейчас не участвуешь.")
        return

    await q.message.reply_text("Ты участвуешь в турнире ✅")

# ================= RULES =================
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    await q.message.reply_text(
        "📜 ПРАВИЛА БИТВЫ НИКОВ\n\n"
        "• 1 голос = 1 участник\n"
        "• Победитель определяется голосами\n"
        "• Финал — 1 победитель\n"
        "• Бот не передаёт личные данные"
    )

# ================= INVITE =================
async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    link = f"https://t.me/{context.bot.username}?start={uid}"

    await q.message.reply_text(f"Твоя ссылка:\n{link}")

# ================= ROUTER =================
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data

    if data == "join":
        await join(update, context)
    elif data == "find_me":
        await find_me(update, context)
    elif data == "rules":
        await rules(update, context)
    elif data == "invite":
        await invite(update, context)

# ================= MAIN =================
def main():
    load_state()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(router))

    print("Бот стабильно запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
