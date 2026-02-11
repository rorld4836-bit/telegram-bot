import os
import sqlite3
import random
import logging
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -100XXXXXXXXXX  # ВСТАВЬ СВОЙ КАНАЛ
BATTLE_TIME = 300  # 5 минут

logging.basicConfig(level=logging.INFO)

# ================= DATABASE =================

conn = sqlite3.connect("battle.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS players (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    alive INTEGER DEFAULT 1
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS votes (
    voter_id INTEGER,
    battle_id INTEGER,
    UNIQUE(voter_id, battle_id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS battles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    p1 INTEGER,
    p2 INTEGER,
    v1 INTEGER DEFAULT 0,
    v2 INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1
)
""")

conn.commit()

current_battle = {
    "id": None,
    "message_id": None
}

# ================= MENU =================

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Участвовать", callback_data="join")],
        [InlineKeyboardButton("📊 Статус", callback_data="status")]
    ])

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 БИТВА НИКОВ 🔥\n\n"
        "Нажми кнопку, чтобы участвовать 👇",
        reply_markup=menu()
    )

# ================= JOIN =================

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    cursor.execute("SELECT 1 FROM players WHERE user_id=?", (user.id,))
    if cursor.fetchone():
        await query.answer("Ты уже участвуешь!", show_alert=True)
        return

    cursor.execute(
        "INSERT INTO players (user_id, username) VALUES (?,?)",
        (user.id, user.username or user.first_name)
    )
    conn.commit()

    await query.answer("Ты добавлен в турнир!", show_alert=True)

# ================= CREATE BATTLE =================

async def create_battle(context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("SELECT user_id FROM players WHERE alive=1")
    players = [p[0] for p in cursor.fetchall()]

    if len(players) < 2:
        return

    p1, p2 = random.sample(players, 2)

    cursor.execute(
        "INSERT INTO battles (p1, p2) VALUES (?,?)",
        (p1, p2)
    )
    battle_id = cursor.lastrowid
    conn.commit()

    current_battle["id"] = battle_id

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔥 Голос за 1", callback_data=f"vote_{battle_id}_1"),
            InlineKeyboardButton("🔥 Голос за 2", callback_data=f"vote_{battle_id}_2")
        ]
    ])

    text = f"🔥 БИТВА 🔥\n\nУчастник 1 VS Участник 2\n\nГолосуй ниже 👇"

    msg = await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=text,
        reply_markup=keyboard
    )

    current_battle["message_id"] = msg.message_id

    context.job_queue.run_once(end_battle, BATTLE_TIME)

# ================= VOTE =================

async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    user = query.from_user
    data = query.data
    await query.answer()

    _, battle_id, choice = data.split("_")
    battle_id = int(battle_id)

    try:
        cursor.execute(
            "INSERT INTO votes (voter_id, battle_id) VALUES (?,?)",
            (user.id, battle_id)
        )
    except:
        await query.answer("Ты уже голосовал!", show_alert=True)
        return

    if choice == "1":
        cursor.execute("UPDATE battles SET v1 = v1 + 1 WHERE id=?", (battle_id,))
    else:
        cursor.execute("UPDATE battles SET v2 = v2 + 1 WHERE id=?", (battle_id,))

    conn.commit()
    await query.answer("Голос засчитан!")

# ================= END BATTLE =================

async def end_battle(context: ContextTypes.DEFAULT_TYPE):

    battle_id = current_battle["id"]

    cursor.execute("SELECT p1, p2, v1, v2 FROM battles WHERE id=?", (battle_id,))
    battle = cursor.fetchone()

    if not battle:
        return

    p1, p2, v1, v2 = battle

    loser = p1 if v1 < v2 else p2

    cursor.execute("UPDATE players SET alive=0 WHERE user_id=?", (loser,))
    cursor.execute("UPDATE battles SET active=0 WHERE id=?", (battle_id,))
    conn.commit()

    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=f"🏆 Победитель определён!\n\nСчёт: {v1} : {v2}"
    )

    cursor.execute("SELECT COUNT(*) FROM players WHERE alive=1")
    alive = cursor.fetchone()[0]

    if alive <= 1:
        await finish_game(context)
    else:
        context.job_queue.run_once(create_battle, 10)

# ================= FINISH =================

async def finish_game(context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("""
        SELECT username FROM players
        WHERE alive=1
        LIMIT 1
    """)
    winner = cursor.fetchone()

    if winner:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"🏆 ПОБЕДИТЕЛЬ ТУРНИРА: {winner[0]}"
        )

    cursor.execute("DELETE FROM players")
    cursor.execute("DELETE FROM votes")
    cursor.execute("DELETE FROM battles")
    conn.commit()

# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(join, pattern="join"))
    app.add_handler(CallbackQueryHandler(vote, pattern="vote_"))

    app.job_queue.run_once(create_battle, 30)

    print("🚀 Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
