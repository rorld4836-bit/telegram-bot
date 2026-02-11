import os
import sqlite3
import random
import logging
from datetime import datetime, timedelta

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

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -100XXXXXXXXX  # сюда вставишь свой канал

logging.basicConfig(level=logging.INFO)

# ===== DATABASE =====

conn = sqlite3.connect("giveaway.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS giveaways (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER,
    end_time TEXT,
    active INTEGER DEFAULT 1
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS participants (
    giveaway_id INTEGER,
    user_id INTEGER,
    UNIQUE(giveaway_id, user_id)
)
""")

conn.commit()

# ===== START =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎉 Бот для проведения розыгрышей!\n\n"
        "Админ: /giveaway 60 (60 минут)"
    )

# ===== CREATE GIVEAWAY =====

async def giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text("Укажи время в минутах.")
        return

    minutes = int(context.args[0])
    end_time = datetime.utcnow() + timedelta(minutes=minutes)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎉 Участвовать", callback_data="join")]
    ])

    msg = await update.message.reply_text(
        f"🎁 РОЗЫГРЫШ!\n\n"
        f"Завершится через {minutes} минут.\n\n"
        f"Нажми кнопку ниже 👇",
        reply_markup=keyboard
    )

    cursor.execute(
        "INSERT INTO giveaways (message_id, end_time) VALUES (?,?)",
        (msg.message_id, end_time.isoformat())
    )
    conn.commit()

# ===== JOIN =====

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user

    cursor.execute("SELECT id FROM giveaways WHERE active=1")
    giveaway = cursor.fetchone()

    if not giveaway:
        await query.answer("Нет активного розыгрыша", show_alert=True)
        return

    giveaway_id = giveaway[0]

    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user.id)
        if member.status not in ["member", "administrator", "creator"]:
            await query.answer("Подпишись на канал!", show_alert=True)
            return
    except:
        await query.answer("Ошибка проверки подписки", show_alert=True)
        return

    try:
        cursor.execute(
            "INSERT INTO participants VALUES (?,?)",
            (giveaway_id, user.id)
        )
        conn.commit()
        await query.answer("Ты участвуешь!")
    except:
        await query.answer("Ты уже участвуешь")

# ===== CHECK END =====

async def check_giveaways(context: ContextTypes.DEFAULT_TYPE):

    now = datetime.utcnow().isoformat()

    cursor.execute(
        "SELECT id, message_id FROM giveaways WHERE active=1 AND end_time <= ?",
        (now,)
    )

    giveaways = cursor.fetchall()

    for giveaway in giveaways:
        giveaway_id, message_id = giveaway

        cursor.execute(
            "SELECT user_id FROM participants WHERE giveaway_id=?",
            (giveaway_id,)
        )
        users = cursor.fetchall()

        if users:
            winner = random.choice(users)[0]
            text = f"🏆 Розыгрыш завершён!\n\nПобедитель: tg://user?id={winner}"
        else:
            text = "Розыгрыш завершён. Участников нет."

        await context.bot.edit_message_text(
            chat_id=context.job.chat_id,
            message_id=message_id,
            text=text
        )

        cursor.execute("UPDATE giveaways SET active=0 WHERE id=?", (giveaway_id,))
        conn.commit()

# ===== MAIN =====

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("giveaway", giveaway))
    app.add_handler(CallbackQueryHandler(join, pattern="join"))

    app.job_queue.run_repeating(check_giveaways, 30)

    app.run_polling()

if __name__ == "__main__":
    main()
