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

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -1003814033445

if not TOKEN:
    raise ValueError("BOT_TOKEN не найден!")

logging.basicConfig(level=logging.INFO)

game_state = {
    "players": {},
    "round": 1,
    "message_id": None
}

# ==========================
# МЕНЮ БОТА
# ==========================

def bot_menu(bot_username):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Перейти в канал", url="https://t.me/БИТВА_НИКОВ")],
        [InlineKeyboardButton("⚔️ Участвовать", callback_data="join")],
        [InlineKeyboardButton("👤 Найти себя", callback_data="me")],
        [InlineKeyboardButton("📜 Правила", callback_data="rules")],
        [InlineKeyboardButton("📩 Пригласить", callback_data="ref")]
    ])

# ==========================
# /START
# ==========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot_username = context.bot.username

    await update.message.reply_text(
        f"""
🔥 <b>БИТВА НИКОВ</b> 🔥

Добро пожаловать, {user.first_name}!

⚔️ Участвуй в турнире
👥 Приглашай друзей
🏆 Побеждай

👇 Всё управление здесь
""",
        parse_mode="HTML",
        reply_markup=bot_menu(bot_username)
    )

# ==========================
# УЧАСТИЕ
# ==========================

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    if user.id in game_state["players"]:
        await query.answer("Ты уже участвуешь!", show_alert=True)
        return

    game_state["players"][user.id] = {
        "name": user.username or user.first_name,
        "score": random.randint(1, 100)
    }

    await query.answer("Ты в игре!", show_alert=True)
    await update_channel_post(context)

# ==========================
# НАЙТИ СЕБЯ
# ==========================

async def find_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    if user.id not in game_state["players"]:
        await query.answer("Ты ещё не участвуешь!", show_alert=True)
        return

    score = game_state["players"][user.id]["score"]

    await query.message.reply_text(
        f"👤 Ты в игре!\n🎯 Твои очки: {score}"
    )

# ==========================
# ПРАВИЛА
# ==========================

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        """
📜 <b>ПРАВИЛА</b>

1️⃣ Турнир — 4 раунда
2️⃣ Раунд длится 7 часов
3️⃣ После каждого раунда часть игроков выбывает
4️⃣ Побеждает лучший

🔥 Удачи!
""",
        parse_mode="HTML"
    )

# ==========================
# РЕФЕРАЛКА
# ==========================

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    link = f"https://t.me/{context.bot.username}?start={user.id}"

    await query.message.reply_text(
        f"📩 Твоя ссылка для приглашения:\n\n{link}"
    )

# ==========================
# ПОСТ В КАНАЛ
# ==========================

async def update_channel_post(context):
    players = list(game_state["players"].values())

    if len(players) < 2:
        text = """
🔥 <b>БИТВА НИКОВ</b> 🔥

⏳ Ожидаем игроков...
Минимум 2 участника
"""
    else:
        p1 = players[0]["name"]
        p2 = players[1]["name"]

        text = f"""
🔥 <b>БИТВА НИКОВ</b> 🔥

🏁 Раунд: {game_state['round']} / 4
👥 Участники: {len(players)}

⚔️ {p1} VS {p2}

⏳ Время раунда: 7 часов

👇 Жми кнопку ниже
"""

    if game_state["message_id"]:
        try:
            await context.bot.edit_message_text(
                chat_id=CHANNEL_ID,
                message_id=game_state["message_id"],
                text=text,
                parse_mode="HTML"
            )
        except:
            pass
    else:
        msg = await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode="HTML"
        )
        game_state["message_id"] = msg.message_id

# ==========================
# ЗАПУСК
# ==========================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(join, pattern="join"))
    app.add_handler(CallbackQueryHandler(find_me, pattern="me"))
    app.add_handler(CallbackQueryHandler(rules, pattern="rules"))
    app.add_handler(CallbackQueryHandler(referral, pattern="ref"))

    print("Бот запущен...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
