import os
import sqlite3
import random
import logging
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ========= НАСТРОЙКИ =========

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -100XXXXXXXXXX  # ВСТАВЬ ID КАНАЛА

if not TOKEN:
    print("❌ BOT_TOKEN не найден!")
    exit()

logging.basicConfig(level=logging.INFO)

# ========= БАЗА =========

conn = sqlite3.connect("giveaway.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS giveaway (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    message_id INTEGER,
    chat_id INTEGER,
    end_time TEXT,
    active INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS participants (
    user_id INTEGER UNIQUE
)
""")

conn.commit()

# ========= START =========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎉 Giveaway Bot v2\n\n"
        "Создать розыгрыш:\n"
        "/giveaway 30"
    )

# ========= СОЗДАНИЕ =========

async def giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("SELECT active FROM giveaway WHERE id=1")
    row = cursor.fetchone()

    if row and row[0] == 1:
        await update.message.reply_text("⚠️ Уже есть активный розыгрыш.")
        return

    if not context.args:
        await update.message.reply_text("Укажи время в минутах.")
        return

    try:
        minutes = int(context.args[0])
    except:
        await update.message.reply_text("Время должно быть числом.")
        return

    end_time = datetime.utcnow() + timedelta(minutes=minutes)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎉 Участвовать", callback_data="join")]
    ])

    msg = await update.message.reply_text(
        f"🎁 РОЗЫГРЫШ\n\n"
        f"⏳ Закончится через {minutes} минут\n\n"
        f"Нажми кнопку 👇",
        reply_markup=keyboard
    )

    cursor.execute("DELETE FROM participants")

    cursor.execute("""
        INSERT OR REPLACE INTO giveaway (id, message_id, chat_id, end_time, active)
        VALUES (1, ?, ?, ?, 1)
    """, (msg.message_id, msg.chat_id, end_time.isoformat()))

    conn.commit()

# ========= УЧАСТИЕ =========

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cursor.execute("SELECT active FROM giveaway WHERE id=1")
    row = cursor.fetchone()

    if not row or row[0] == 0:
        await query.answer("Нет активного розыгрыша", show_alert=True)
        return

    user = query.from_user

    # Проверка подписки
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user.id)
        if member.status not in ["member", "administrator", "creator"]:
            await query.answer("Подпишись на канал!", show_alert=True)
            return
    except:
        await query.answer("Ошибка проверки подписки", show_alert=True)
        return

    try:
        cursor.execute("INSERT INTO participants VALUES (?)", (user.id,))
        conn.commit()
        await query.answer("Ты участвуешь!")
    except:
        await query.answer("Ты уже участвуешь!")

# ========= ПРОВЕРКА =========

async def check_giveaway(context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("SELECT message_id, chat_id, end_time, active FROM giveaway WHERE id=1")
    row = cursor.fetchone()

    if not row:
        return

    message_id, chat_id, end_time, active = row

    if active == 0:
        return

    if datetime.utcnow() >= datetime.fromisoformat(end_time):

        cursor.execute("SELECT user_id FROM participants")
        users = cursor.fetchall()

        if users:
            winner = random.choice(users)[0]
            text = f"🏆 Розыгрыш завершён!\n\nПобедитель:\n[tg://user?id={winner}](tg://user?id={winner})"
        else:
            text = "Розыгрыш завершён.\nУчастников нет."

        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode="Markdown"
            )
        except:
            pass

        cursor.execute("UPDATE giveaway SET active=0 WHERE id=1")
        conn.commit()

# ========= MAIN =========

def main():
    print("🚀 Giveaway Bot v2 запущен")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("giveaway", giveaway))
    app.add_handler(CallbackQueryHandler(join, pattern="join"))

    app.job_queue.run_repeating(check_giveaway, 20)

    app.run_polling()

if __name__ == "__main__":
    main()
