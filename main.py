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
    ContextTypes,
    filters
)

# ========== НАСТРОЙКИ ==========
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = "@battlertf"
ROUND_DURATION = 14 * 60 * 60

ROUND_LIMITS = {1: 5, 2: 10, 3: 15, 4: 25, 5: 27}
DATA_FILE = "data.json"
# ===============================

logging.basicConfig(level=logging.INFO)

# ========== ДАННЫЕ ==========
def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "active": False,
            "round": 1,
            "round_start": None,
            "players": {}
        }
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(DATA, f, indent=2)

DATA = load_data()

# ========== МЕНЮ ==========
def reply_menu():
    return ReplyKeyboardMarkup(
        [
            ["⚔️ Участвовать", "📊 Мой статус"],
            ["📜 Правила", "🔗 Пригласить"]
        ],
        resize_keyboard=True
    )

# ========== ПРАВИЛА ==========
RULES = (
    "📜 *Правила «Битва ников»*\n\n"
    "• Турнир состоит из раундов\n"
    "• Раунд длится 14 часов (общий таймер)\n"
    "• Битв может быть несколько\n"
    "• Проигравшие ждут следующий турнир\n\n"
    "🔥 Раунд 4 — редкий\n"
    "🔥 Раунд 5 — очень редкий и финальный\n\n"
    "🏆 Победитель всегда ОДИН\n\n"
    "🔒 *Конфиденциальность*\n"
    "Бот хранит только ник и ID Telegram.\n"
    "Личные данные не собираются и не передаются."
)

# ========== START ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)

    if uid not in DATA["players"]:
        DATA["players"][uid] = {
            "username": user.username,
            "score": 0,
            "joined": time.time(),
            "reach": None
        }
        save_data()

    await update.message.reply_text(
        "🔥 Добро пожаловать в *Битву ников*!",
        parse_mode="Markdown",
        reply_markup=reply_menu()
    )

# ========== КНОПКИ ==========
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = str(update.effective_user.id)

    if text == "📜 Правила":
        await update.message.reply_text(RULES, parse_mode="Markdown", reply_markup=reply_menu())

    elif text == "🔗 Пригласить":
        link = f"https://t.me/{context.bot.username}?start={uid}"
        await update.message.reply_text(f"🔗 Твоя ссылка:\n{link}", reply_markup=reply_menu())

    elif text == "📊 Мой статус":
        p = DATA["players"].get(uid)
        if not p:
            await update.message.reply_text("Ты ещё не участвуешь.", reply_markup=reply_menu())
            return

        await update.message.reply_text(
            f"📊 *Твой статус*\n"
            f"Раунд: {DATA['round']}\n"
            f"Приглашения: {p['score']} / {ROUND_LIMITS[DATA['round']]}",
            parse_mode="Markdown",
            reply_markup=reply_menu()
        )

    elif text == "⚔️ Участвовать":
        if not DATA["active"]:
            DATA["active"] = True
            DATA["round_start"] = time.time()
            save_data()

            buttons = InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("⚔️ Участвовать", url=f"https://t.me/{context.bot.username}"),
                    InlineKeyboardButton("📨 Пригласить", url=f"https://t.me/{context.bot.username}?start={uid}")
                ]]
            )

            await context.bot.send_message(
                chat_id=CHANNEL,
                text=(
                    f"⚔️ *Битва ников*\n\n"
                    f"Раунд {DATA['round']}\n"
                    f"⏳ Время: 14 часов"
                ),
                parse_mode="Markdown",
                reply_markup=buttons
            )

        await update.message.reply_text("✅ Ты участвуешь!", reply_markup=reply_menu())

# ========== РЕФЕРАЛ ==========
async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    args = context.args

    if args:
        ref = args[0]
        if ref in DATA["players"] and ref != uid:
            DATA["players"][ref]["score"] += 1
            if DATA["round"] == 5 and DATA["players"][ref]["reach"] is None:
                DATA["players"][ref]["reach"] = time.time()
            save_data()

    await start(update, context)

# ========== ЗАПУСК ==========
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", referral))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
    print("🤖 Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
