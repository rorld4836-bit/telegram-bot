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

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN not found")

CHANNEL = "@battlertf"
ROUND_DURATION = 14 * 60 * 60  # 14 часов

ROUND_LIMITS = {
    1: 5,
    2: 10,
    3: 15,
    4: 25,  # редкий
    5: 27   # очень редкий, финал
}

DATA_FILE = "data.json"
# =============================================

logging.basicConfig(level=logging.INFO)

# ================= ХРАНЕНИЕ ==================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "tournament_active": False,
            "round": 1,
            "round_start": None,
            "players": {},
            "finished": []
        }
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(DATA, f, indent=2)

DATA = load_data()

# ================= UI ==================
def main_menu():
    return ReplyKeyboardMarkup(
        [
            ["⚔️ Участвовать", "📊 Мой статус"],
            ["📜 Правила", "🔗 Пригласить"]
        ],
        resize_keyboard=True
    )

# ================= ПРАВИЛА ==================
RULES_TEXT = (
    "📜 *Правила турнира «Битва ников»*\n\n"
    "1️⃣ Турнир проходит в несколько раундов. Участие бесплатное.\n\n"
    "2️⃣ Каждый раунд длится 14 часов. Таймер общий для всех.\n\n"
    "3️⃣ В одном раунде может идти несколько битв.\n\n"
    "4️⃣ Проигравшие выбывают и ждут следующий турнир.\n\n"
    "5️⃣ Раунд 4 — редкий. Раунд 5 — очень редкий и финальный.\n\n"
    "6️⃣ В 5 раунде все участники соревнуются вместе.\n"
    "Победитель всегда ОДИН.\n\n"
    "7️⃣ Тай-брейк (только 5 раунд):\n"
    "побеждает тот, кто первым достиг лимита.\n\n"
    "8️⃣ Награды выдаются вручную организатором.\n\n"
    "🔒 *Конфиденциальность*\n"
    "Бот не хранит личные данные, кроме публичного никнейма\n"
    "и технического ID Telegram. Данные никуда не передаются."
)

# ================= ЛОГИКА ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)

    if uid not in DATA["players"]:
        DATA["players"][uid] = {
            "username": user.username,
            "score": 0,
            "joined": time.time(),
            "reach_time": None
        }
        save_data()

    await update.message.reply_text(
        "🔥 Добро пожаловать в *Битву ников*!",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = str(update.effective_user.id)

    if text == "📜 Правила":
        await update.message.reply_text(RULES_TEXT, parse_mode="Markdown")

    elif text == "🔗 Пригласить":
        link = f"https://t.me/{context.bot.username}?start={uid}"
        await update.message.reply_text(f"🔗 Твоя ссылка:\n{link}")

    elif text == "📊 Мой статус":
        if uid not in DATA["players"]:
            await update.message.reply_text("Ты ещё не участвуешь.")
            return

        p = DATA["players"][uid]
        await update.message.reply_text(
            f"📊 *Твой статус*\n\n"
            f"Раунд: {DATA['round']}\n"
            f"Приглашения: {p['score']} / {ROUND_LIMITS[DATA['round']]}",
            parse_mode="Markdown"
        )

    elif text == "⚔️ Участвовать":
        if not DATA["tournament_active"]:
            DATA["tournament_active"] = True
            DATA["round_start"] = time.time()
            save_data()

            await context.bot.send_message(
                chat_id=CHANNEL,
                text=f"⚔️ *Начался раунд {DATA['round']}!*\n"
                     f"⏳ Время: 14 часов\n"
                     f"🔗 Участвовать: https://t.me/{context.bot.username}",
                parse_mode="Markdown"
            )

        await update.message.reply_text("✅ Ты участвуешь!")

# ================= РЕФЕРАЛЫ ==================
async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    args = context.args

    if args:
        ref = args[0]
        if ref in DATA["players"] and ref != uid:
            DATA["players"][ref]["score"] += 1

            if DATA["round"] == 5:
                if DATA["players"][ref]["reach_time"] is None:
                    DATA["players"][ref]["reach_time"] = time.time()

            save_data()

    await start(update, context)

# ================= ТАЙМЕР ==================
async def timer_job(context: ContextTypes.DEFAULT_TYPE):
    if not DATA["tournament_active"]:
        return

    elapsed = time.time() - DATA["round_start"]
    remaining = ROUND_DURATION - elapsed

    if remaining <= 0:
        await finish_round(context)

async def finish_round(context):
    limit = ROUND_LIMITS[DATA["round"]]
    winners = []

    for uid, p in DATA["players"].items():
        if p["score"] >= limit:
            winners.append(uid)

    if len(winners) == 1 or DATA["round"] >= 5:
        winner = winners[0] if winners else max(
            DATA["players"],
            key=lambda u: (
                DATA["players"][u]["score"],
                -DATA["players"][u]["reach_time"]
                if DATA["players"][u]["reach_time"] else float("inf")
            )
        )

        await context.bot.send_message(
            chat_id=CHANNEL,
            text=f"🏆 *Победитель турнира*\n\n"
                 f"👑 @{DATA['players'][winner]['username']}",
            parse_mode="Markdown"
        )

        DATA["tournament_active"] = False
        DATA["round"] = 1
        DATA["players"] = {}
        save_data()
        return

    DATA["round"] += 1
    DATA["round_start"] = time.time()

    for uid in winners:
        DATA["players"][uid]["score"] = 0

    save_data()

    await context.bot.send_message(
        chat_id=CHANNEL,
        text=f"🔥 *Начался раунд {DATA['round']}!*",
        parse_mode="Markdown"
    )

# ================= ЗАПУСК ==================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", referral))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

    app.job_queue.run_repeating(timer_job, interval=60)

    print("🤖 Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
