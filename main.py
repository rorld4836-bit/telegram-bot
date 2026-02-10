import os
import logging
import time
from collections import defaultdict
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================== НАСТРОЙКИ ==================
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в Variables")

BATTLE_CHANNEL_LINK = "https://t.me/battlertf"

ROUNDS = {
    1: 5,
    2: 10,
    3: 15,
    4: 25,
    5: 27  # редкий раунд с тай-брейком
}

ROUND_TIME = 14 * 60 * 60
# ==============================================

logging.basicConfig(level=logging.INFO)

users = {}
referrals = defaultdict(int)
round_reach_time = {}

# ================== КОМАНДЫ ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in users:
        users[user_id] = {"round": 1}

    keyboard = [
        [InlineKeyboardButton("⚔️ Участвовать", callback_data="join")],
        [InlineKeyboardButton("📜 Правила", callback_data="rules")]
    ]

    await update.message.reply_text(
        "🔥 *Битва Ников*\n\nГотов доказать силу своего ника?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "📜 *Правила*\n\n"
        "• Участие бесплатное\n"
        "• Проигравшие не вылетают\n"
        "• В 5 раунде возможен тай-брейк\n"
        "• Награды выдаются вручную\n"
        "• Накрутка запрещена",
        parse_mode="Markdown"
    )

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    ref_link = f"https://t.me/{context.bot.username}?start={user_id}"

    keyboard = [
        [InlineKeyboardButton("⚔️ Перейти в канал битв", url=BATTLE_CHANNEL_LINK)],
        [InlineKeyboardButton("📨 Пригласить", url=f"https://t.me/share/url?url={ref_link}")]
    ]

    await query.answer()
    await query.message.reply_text(
        f"✅ Ты участвуешь!\n\n"
        f"🔗 Твоя реферальная ссылка:\n{ref_link}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================== РЕФЕРАЛЫ ==================
async def referral_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user_id = update.effective_user.id

    if args:
        referrer = int(args[0])
        if user_id != referrer:
            referrals[referrer] += 1

            if users.get(referrer, {}).get("round") == 5:
                if referrer not in round_reach_time:
                    round_reach_time[referrer] = time.time()

    await start(update, context)

# ================== ЗАПУСК ==================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", referral_start))
    app.add_handler(CallbackQueryHandler(join, pattern="join"))
    app.add_handler(CallbackQueryHandler(rules, pattern="rules"))

    print("🤖 Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
