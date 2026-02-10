import os
import json
import time
import logging
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ========= НАСТРОЙКИ =========
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = "@battlertf"
ROUND_DURATION = 14 * 60 * 60
ROUND_LIMITS = {1: 5, 2: 10, 3: 15, 4: 25, 5: 27}
DATA_FILE = "data.json"
# =============================

logging.basicConfig(level=logging.INFO)

# ========= ДАННЫЕ =========
def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "active": False,
            "round": 1,
            "round_start": None,
            "players": {},
            "votes": {}
        }
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(DATA, f, indent=2)

DATA = load_data()

# ========= МЕНЮ =========
def reply_menu():
    return ReplyKeyboardMarkup(
        [
            ["⚔️ Участвовать", "📊 Мой статус"],
            ["📜 Правила", "🔗 Пригласить"]
        ],
        resize_keyboard=True
    )

# ========= START =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)

    if uid not in DATA["players"]:
        DATA["players"][uid] = {
            "username": user.username,
            "score": 0
        }
        save_data()

    await update.message.reply_text(
        "🔥 Добро пожаловать в *Битву ников!*\n\n"
        "Турнир проходит в канале:\n"
        f"👉 https://t.me/battlertf",
        parse_mode="Markdown",
        reply_markup=reply_menu()
    )

# ========= КНОПКИ =========
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = str(update.effective_user.id)

    if text == "⚔️ Участвовать":
        if not DATA["active"]:
            DATA["active"] = True
            DATA["round_start"] = time.time()

            players = list(DATA["players"].values())
            if len(players) >= 2:
                p1, p2 = players[0], players[1]

                buttons = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("⚔️ Участвовать", url=f"https://t.me/{context.bot.username}"),
                            InlineKeyboardButton("📨 Пригласить", url=f"https://t.me/{context.bot.username}")
                        ],
                        [
                            InlineKeyboardButton("👍 Проголосовать", callback_data="vote")
                        ]
                    ]
                )

                await context.bot.send_message(
                    chat_id=CHANNEL,
                    text=(
                        f"⚔️ *Битва ников*\n\n"
                        f"Раунд {DATA['round']}\n"
                        f"@{p1['username']} 🆚 @{p2['username']}\n\n"
                        f"⏳ Время: 14 часов"
                    ),
                    parse_mode="Markdown",
                    reply_markup=buttons
                )

            save_data()

        await update.message.reply_text("✅ Ты участвуешь!", reply_markup=reply_menu())

    elif text == "📊 Мой статус":
        p = DATA["players"].get(uid)
        if not p:
            return
        await update.message.reply_text(
            f"📊 Твой статус\n"
            f"Раунд: {DATA['round']}\n"
            f"Голоса: {p['score']}",
            reply_markup=reply_menu()
        )

    elif text == "🔗 Пригласить":
        link = f"https://t.me/{context.bot.username}?start={uid}"
        await update.message.reply_text(f"🔗 Твоя ссылка:\n{link}", reply_markup=reply_menu())

# ========= ГОЛОСОВАНИЕ =========
async def vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)

    if user_id in DATA["votes"]:
        await query.answer("Ты уже голосовал 👍", show_alert=True)
        return

    # голос идёт первому участнику битвы
    first_player = list(DATA["players"].keys())[0]
    DATA["players"][first_player]["score"] += 1
    DATA["votes"][user_id] = True
    save_data()

    await query.answer("Голос засчитан 👍")

# ========= ЗАПУСК =========
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
    app.add_handler(CallbackQueryHandler(vote_callback))

    print("🤖 Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
