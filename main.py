import logging
import random
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================= НАСТРОЙКИ =================

TOKEN = os.getenv("BOT_TOKEN")  # Берём токен из Railway
CHANNEL_ID = -1001234567890  # <-- ВСТАВЬ ID КАНАЛА
ROUND_DURATION = 7 * 60 * 60  # 7 часов
MIN_PLAYERS = 2

if not TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных Railway!")

# ================= ЛОГИ =================

logging.basicConfig(level=logging.WARNING)

# ================= СОСТОЯНИЕ ИГРЫ =================

game_state = {
    "players": {},
    "round": 1,
    "active": False,
    "message_id": None
}

# ================= КРАСИВЫЙ ПОСТ =================

def build_post_text():
    players_text = ""

    if game_state["players"]:
        for p in game_state["players"].values():
            players_text += (
                f"⚔️ {p['nickname']} | "
                f"🎯 Очки: {p['score']} | "
                f"👥 Пригласил: {p['referrals']}\n"
            )
    else:
        players_text = "Пока нет участников"

    return f"""
🔥 <b>БИТВА НИКОВ</b> 🔥

🏁 Раунд: {game_state['round']} / 4
👥 Игроков: {len(game_state['players'])}

{players_text}

⏳ Раунд длится 7 часов
👑 В финале останется только один
🎁 Каждый приглашённый даёт +5 очков

Жми кнопку ниже 👇
"""

# ================= КНОПКИ =================

def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚔️ Участвовать", callback_data="join"),
            InlineKeyboardButton("📩 Пригласить", callback_data="ref")
        ]
    ])

# ================= СТАРТ =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if args:
        try:
            referrer_id = int(args[0])
            user_id = update.effective_user.id

            if (
                referrer_id != user_id
                and referrer_id in game_state["players"]
            ):
                game_state["players"][referrer_id]["referrals"] += 1
        except:
            pass

    await update.message.reply_text(
        "🔥 Добро пожаловать в БИТВУ НИКОВ!\n\n"
        "Переходи в канал и участвуй!"
    )

# ================= УЧАСТИЕ =================

async def join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    if user.id in game_state["players"]:
        await query.answer("Ты уже участвуешь!", show_alert=True)
        return

    game_state["players"][user.id] = {
        "nickname": user.username or user.first_name,
        "score": random.randint(1, 100),
        "referrals": 0
    }

    await query.answer("Ты вступил в турнир!", show_alert=True)

    if not game_state["active"] and len(game_state["players"]) >= MIN_PLAYERS:
        game_state["active"] = True
        context.job_queue.run_once(end_round, ROUND_DURATION)

    await update_post(context)

# ================= РЕФЕРАЛКА =================

async def referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    link = f"https://t.me/{context.bot.username}?start={user.id}"

    await query.message.reply_text(
        f"📩 Твоя реферальная ссылка:\n\n{link}"
    )

# ================= РАУНДЫ =================

async def end_round(context: ContextTypes.DEFAULT_TYPE):

    if len(game_state["players"]) < MIN_PLAYERS:
        game_state["active"] = False
        return

    for p in game_state["players"].values():
        p["score"] += p["referrals"] * 5

    sorted_players = sorted(
        game_state["players"].items(),
        key=lambda x: x[1]["score"],
        reverse=True
    )

    if game_state["round"] >= 4:
        winner = sorted_players[0][1]

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"""
🏆 <b>ФИНАЛ ТУРНИРА!</b> 🏆

👑 Победитель:
<b>{winner['nickname']}</b>

🔥 Новый турнир начнётся через 30 секунд...
""",
            parse_mode="HTML"
        )

        game_state["players"] = {}
        game_state["round"] = 1
        game_state["active"] = False
        game_state["message_id"] = None

        context.job_queue.run_once(start_new_tournament, 30)
        return

    survivors = dict(sorted_players[:max(1, len(sorted_players)//2)])

    game_state["players"] = survivors
    game_state["round"] += 1

    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=f"🔥 Начался раунд {game_state['round']}!\nИгроков осталось: {len(survivors)}",
        parse_mode="HTML"
    )

    context.job_queue.run_once(end_round, ROUND_DURATION)
    await update_post(context)

# ================= НОВЫЙ ТУРНИР =================

async def start_new_tournament(context: ContextTypes.DEFAULT_TYPE):
    await update_post(context)

# ================= ОБНОВЛЕНИЕ ПОСТА =================

async def update_post(context: ContextTypes.DEFAULT_TYPE):
    text = build_post_text()

    if game_state["message_id"]:
        try:
            await context.bot.edit_message_text(
                chat_id=CHANNEL_ID,
                message_id=game_state["message_id"],
                text=text,
                parse_mode="HTML",
                reply_markup=main_keyboard()
            )
        except:
            pass
    else:
        msg = await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
        game_state["message_id"] = msg.message_id

# ================= ЗАПУСК =================

async def on_startup(application):
    await application.bot.initialize()
    await update_post(application)

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(join_callback, pattern="join"))
    app.add_handler(CallbackQueryHandler(referral_callback, pattern="ref"))

    app.post_init = on_startup

    print("Бот запущен...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
