import os
import logging
import sqlite3
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -1003814033445  # ТВОЙ ID КАНАЛА

logging.basicConfig(level=logging.INFO)

if not TOKEN:
    raise ValueError("BOT_TOKEN не найден!")

# ================= DATABASE =================

conn = sqlite3.connect("battle.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS players (
    user_id INTEGER PRIMARY KEY,
    username TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS votes (
    voter_id INTEGER,
    battle_id INTEGER,
    UNIQUE(voter_id, battle_id)
)
""")

conn.commit()

# ================= СОСТОЯНИЕ БИТВЫ =================

current_battle = {
    "p1": None,
    "p2": None,
    "v1": 0,
    "v2": 0,
    "message_id": None,
    "active": False
}

# ================= МЕНЮ =================

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Участвовать", callback_data="join")],
        [InlineKeyboardButton("👤 Найти себя", callback_data="me")],
        [InlineKeyboardButton("📜 Правила", callback_data="rules")]
    ])

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 <b>БИТВА НИКОВ</b> 🔥\n\n"
        "Нажми участвовать — и если вас станет двое,\n"
        "битва начнётся автоматически 👇",
        parse_mode="HTML",
        reply_markup=menu()
    )

# ================= JOIN =================

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    username = user.username if user.username else user.first_name

    cursor.execute("INSERT OR IGNORE INTO players (user_id, username) VALUES (?,?)",
                   (user.id, username))
    conn.commit()

    await query.answer("✅ Ты в игре!", show_alert=True)

    # Проверяем количество игроков
    cursor.execute("SELECT user_id FROM players")
    players = cursor.fetchall()

    if len(players) >= 2 and not current_battle["active"]:
        await asyncio.sleep(1)
        await create_battle(context)

# ================= CREATE BATTLE =================

async def create_battle(context: ContextTypes.DEFAULT_TYPE):
    try:
        cursor.execute("SELECT user_id, username FROM players LIMIT 2")
        players = cursor.fetchall()

        if len(players) < 2:
            return

        p1_id, p1_name = players[0]
        p2_id, p2_name = players[1]

        current_battle.update({
            "p1": p1_id,
            "p2": p2_id,
            "v1": 0,
            "v2": 0,
            "active": True
        })

        text = (
            "🔥 <b>БИТВА НИКОВ</b> 🔥\n\n"
            f"{p1_name} 🆚 {p2_name}\n\n"
            "📊 Голоса:\n"
            "1️⃣ 0\n"
            "2️⃣ 0\n\n"
            "Голосовать 👍 ответом на сообщение"
        )

        msg = await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode="HTML"
        )

        current_battle["message_id"] = msg.message_id
        logging.info("Битва создана")

    except Exception as e:
        logging.error(f"Ошибка отправки в канал: {e}")

# ================= VOTE =================

async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not current_battle["active"]:
            return

        if update.message.chat_id != CHANNEL_ID:
            return

        if not update.message.reply_to_message:
            return

        if update.message.reply_to_message.message_id != current_battle["message_id"]:
            return

        if update.message.text != "👍":
            return

        voter = update.message.from_user.id

        # защита от повторного голосования
        try:
            cursor.execute("INSERT INTO votes (voter_id, battle_id) VALUES (?,?)",
                           (voter, current_battle["message_id"]))
            conn.commit()
        except:
            return

        if voter == current_battle["p1"]:
            current_battle["v1"] += 1
        elif voter == current_battle["p2"]:
            current_battle["v2"] += 1
        else:
            return

        new_text = (
            "🔥 <b>БИТВА НИКОВ</b> 🔥\n\n"
            f"Голоса:\n"
            f"1️⃣ {current_battle['v1']}\n"
            f"2️⃣ {current_battle['v2']}\n\n"
            "Голосовать 👍"
        )

        await context.bot.edit_message_text(
            chat_id=CHANNEL_ID,
            message_id=current_battle["message_id"],
            text=new_text,
            parse_mode="HTML"
        )

    except Exception as e:
        logging.error(f"Ошибка голосования: {e}")

# ================= FIND ME =================

async def find_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cursor.execute("SELECT 1 FROM players WHERE user_id=?",
                   (query.from_user.id,))
    result = cursor.fetchone()

    if result:
        await query.answer("✅ Ты участвуешь", show_alert=True)
    else:
        await query.answer("❌ Ты не участвуешь", show_alert=True)

# ================= RULES =================

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "📜 <b>Правила</b>\n\n"
        "• 1 человек = 1 голос\n"
        "• Двойные голоса запрещены\n"
        "• Победитель один\n"
        "• Бот защищён от накрутки",
        parse_mode="HTML"
    )

# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(join, pattern="join"))
    app.add_handler(CallbackQueryHandler(find_me, pattern="me"))
    app.add_handler(CallbackQueryHandler(rules, pattern="rules"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, vote))

    print("🚀 ЖЕЛЕЗОБЕТОННЫЙ БОТ ЗАПУЩЕН")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
