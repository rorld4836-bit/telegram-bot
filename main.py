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
CHANNEL_ID = -1003814033445
ROUND_TIME = 120  # Примерное время в секундах для теста (1 раунд 2 минуты)

logging.basicConfig(level=logging.INFO)

if not TOKEN:
    raise ValueError("BOT_TOKEN не найден!")

# ================= DATABASE =================

conn = sqlite3.connect("battle.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS players (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    invited INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS referrals (
    referrer_id INTEGER,
    invited_id INTEGER UNIQUE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS battles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round INTEGER,
    message_id INTEGER,
    active INTEGER DEFAULT 1
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS battle_players (
    battle_id INTEGER,
    user_id INTEGER,
    votes INTEGER DEFAULT 0
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
    "active": False,
    "round": 1
}

# ================= МЕНЮ =================

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Участвовать", callback_data="join")],
        [InlineKeyboardButton("👤 Профиль", callback_data="me")],
        [InlineKeyboardButton("📩 Пригласить", callback_data="ref")],
        [InlineKeyboardButton("📜 Правила", callback_data="rules")]
    ])

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username if user.username else user.first_name

    cursor.execute("INSERT OR IGNORE INTO players (user_id, username) VALUES (?,?)",
                   (user.id, username))
    conn.commit()

    await update.message.reply_text(
        "🔥 <b>БИТВА НИКОВ</b> 🔥\n\n"
        "Добро пожаловать в турнир!\n"
        "Нажми участвовать 👇",
        parse_mode="HTML",
        reply_markup=menu()
    )

# ================= JOIN =================

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    cursor.execute("SELECT COUNT(*) FROM battles WHERE active=1")
    active = cursor.fetchone()[0]

    if active > 10:
        await update.message.reply_text("⏳ Слишком много активных битв, подожди")
        return

    # создаём новую битву
    cursor.execute("INSERT INTO battles (round) VALUES (1)")
    battle_id = cursor.lastrowid

    cursor.execute("INSERT INTO battle_players (battle_id, user_id) VALUES (?,?)",
                   (battle_id, user.id))
    conn.commit()

    await update.message.reply_text("⏳ Ожидаем второго участника...")

    # проверяем есть ли второй
    cursor.execute("""
        SELECT battle_id FROM battle_players
        GROUP BY battle_id
        HAVING COUNT(user_id)=2
        ORDER BY battle_id DESC
        LIMIT 1
    """)
    ready = cursor.fetchone()

    if ready:
        await create_battle(context, ready[0])

# ================= CREATE BATTLE =================

async def create_battle(context, battle_id):
    cursor.execute("""
        SELECT user_id FROM battle_players
        WHERE battle_id=?
    """, (battle_id,))
    players = cursor.fetchall()

    if len(players) != 2:
        return

    p1 = players[0][0]
    p2 = players[1][0]

    cursor.execute("SELECT username FROM players WHERE user_id=?", (p1,))
    p1_name = cursor.fetchone()[0]

    cursor.execute("SELECT username FROM players WHERE user_id=?", (p2,))
    p2_name = cursor.fetchone()[0]

    text = (
        f"🔥 БИТВА НИКОВ 🔥\n\n"
        f"🏆 Раунд: {current_battle['round']}\n\n"
        f"{p1_name} 🆚 {p2_name}\n\n"
        "Голосуй 👍 ответом"
    )

    msg = await context.bot.send_message(CHANNEL_ID, text)

    cursor.execute("UPDATE battles SET message_id=? WHERE id=?",
                   (msg.message_id, battle_id))
    conn.commit()

    asyncio.create_task(round_timer(context, battle_id))

# ================= ROUND TIMER =================

async def round_timer(context, battle_id):
    await asyncio.sleep(ROUND_TIME)

    cursor.execute("""
        SELECT user_id, votes FROM battle_players
        WHERE battle_id=?
        ORDER BY votes DESC
    """, (battle_id,))
    players = cursor.fetchall()

    if len(players) < 2:
        return

    winner = players[0][0]

    cursor.execute("UPDATE battles SET active=0 WHERE id=?", (battle_id,))
    conn.commit()

    cursor.execute("SELECT username FROM players WHERE user_id=?", (winner,))
    name = cursor.fetchone()[0]

    await context.bot.send_message(
        CHANNEL_ID,
        f"🏆 Победитель битвы #{battle_id}: {name}"
    )

# ================= VOTE =================

async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id != CHANNEL_ID:
        return

    if update.message.text != "👍":
        return

    reply = update.message.reply_to_message
    if not reply:
        return

    cursor.execute("SELECT id FROM battles WHERE message_id=? AND active=1",
                   (reply.message_id,))
    battle = cursor.fetchone()

    if not battle:
        return

    battle_id = battle[0]
    voter = update.message.from_user.id

    try:
        cursor.execute("INSERT INTO votes (voter_id, battle_id) VALUES (?,?)",
                       (voter, battle_id))
    except:
        return

    cursor.execute("""
        UPDATE battle_players
        SET votes = votes + 1
        WHERE battle_id=? AND user_id=?
    """, (battle_id, voter))
    conn.commit()

# ================= Профиль =================

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cursor.execute("SELECT invited FROM players WHERE user_id=?",
                   (query.from_user.id,))
    data = cursor.fetchone()

    if data:
        await query.message.reply_text(
            f"👤 Ты пригласил: {data[0]} человек"
        )
    else:
        await query.message.reply_text("Ты ещё не участвуешь.")

# ================= РЕФЕРАЛКА =================

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    link = f"https://t.me/{context.bot.username}?start={query.from_user.id}"

    await query.message.reply_text(
        f"📩 Твоя реферальная ссылка:\n{link}\n\n"
        "1 приглашённый = +1 к счётчику"
    )

# ================= RULES =================

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "📜 <b>ПРАВИЛА</b>\n\n"
        "• 1 приглашённый = 1 участник\n"
        "• Самоприглашение запрещено\n"
        "• Один человек засчитывается один раз\n"
        "• Победитель один\n"
        "• В конце награда 50–500 ⭐\n\n"
        "Бот защищён от накрутки.",
        parse_mode="HTML"
    )

# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, vote))

    print("🚀 PRODUCTION БОТ ЗАПУЩЕН")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
