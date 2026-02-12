import os
import logging
import sqlite3
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
GROUP_LINK = "https://t.me/ТВОЯ_ССЫЛКА_НА_ГРУППУ"
ROUND_TIME = 7 * 60 * 60  # 7 часов

ROUND_REQUIREMENTS = {
    1: 0,
    2: 10,
    3: 15,
    4: 20,
    5: 23
}

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
    invited INTEGER DEFAULT 0,
    alive INTEGER DEFAULT 1
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS referrals (
    referrer_id INTEGER,
    invited_id INTEGER UNIQUE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS game (
    id INTEGER PRIMARY KEY,
    round INTEGER,
    active INTEGER
)
""")

cursor.execute("INSERT OR IGNORE INTO game (id, round, active) VALUES (1, 1, 0)")
conn.commit()

# ================= BATTLE STATE =================

current_battle = {
    "p1": None,
    "p2": None,
    "v1": 0,
    "v2": 0,
    "message_id": None
}

# ================= MENU =================

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Участвовать", callback_data="join")],
        [InlineKeyboardButton("👤 Найти себя", callback_data="me")],
        [InlineKeyboardButton("📜 Правила", callback_data="rules")],
        [InlineKeyboardButton("📩 Пригласить", callback_data="ref")]
    ])

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    if args:
        try:
            ref_id = int(args[0])
            if ref_id != user.id:
                cursor.execute("SELECT 1 FROM referrals WHERE invited_id=?", (user.id,))
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT OR IGNORE INTO referrals (referrer_id, invited_id) VALUES (?,?)",
                        (ref_id, user.id)
                    )
                    cursor.execute(
                        "UPDATE players SET invited = invited + 1 WHERE user_id=?",
                        (ref_id,)
                    )
                    conn.commit()
        except:
            pass

    await update.message.reply_text(
        "🔥 <b>БИТВА НИКОВ</b> 🔥\n\n"
        "Добро пожаловать в главный турнир ников!\n\n"
        f"💬 Группа проекта:\n{GROUP_LINK}\n\n"
        "Выбери действие 👇",
        parse_mode="HTML",
        reply_markup=menu()
    )

# ================= JOIN =================

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    cursor.execute("SELECT 1 FROM players WHERE user_id=?", (user.id,))
    if cursor.fetchone():
        await query.answer("⚠️ Ты уже участвуешь!", show_alert=True)
        return

    cursor.execute(
        "INSERT INTO players (user_id, username) VALUES (?,?)",
        (user.id, user.username or user.first_name)
    )
    conn.commit()

    await query.answer("🔥 Ты в игре!", show_alert=True)

# ================= FIND ME =================

async def find_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    cursor.execute(
        "SELECT invited FROM players WHERE user_id=?",
        (user.id,)
    )
    result = cursor.fetchone()

    if not result:
        await query.answer("❌ Ты не участвуешь!", show_alert=True)
        return

    await query.message.reply_text(
        f"👤 Ты пригласил: {result[0]} участников"
    )

# ================= RULES =================

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        """
📜 <b>ПРАВИЛА</b>

1 приглашённый = 1 участник
Самоприглашение запрещено
Один человек засчитывается один раз
Раунды автоматически каждые 7 часов

Раунд 2 — 10 приглашений
Раунд 3 — 15 приглашений
Раунд 4 — 20 приглашений
Раунд 5 — 23 приглашения (по скорости)

🔒 Данные используются только для турнира.
""",
        parse_mode="HTML"
    )

# ================= REF =================

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    link = f"https://t.me/{context.bot.username}?start={user.id}"
    await query.message.reply_text(f"📩 Твоя ссылка:\n{link}")

# ================= CREATE BATTLE =================

async def create_battle(context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("""
        SELECT user_id, username FROM players
        WHERE alive=1
        LIMIT 2
    """)
    players = cursor.fetchall()

    if len(players) < 2:
        return

    p1_id, p1_name = players[0]
    p2_id, p2_name = players[1]

    current_battle["p1"] = p1_id
    current_battle["p2"] = p2_id
    current_battle["v1"] = 0
    current_battle["v2"] = 0

    text = (
        "🔥 <b>Битва Ников</b> 🔥\n\n"
        "🏆 Раунд: 1\n"
        "👥 Участников: 2\n\n"
        f"@{p1_name} VS @{p2_name}\n\n"
        "📊 Количество голосов:\n"
        "Участник 1: 0\n"
        "Участник 2: 0\n\n"
        "Голосовать 👍 (ответом на сообщение)"
    )

    msg = await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=text,
        parse_mode="HTML"
    )

    current_battle["message_id"] = msg.message_id

# ================= VOTE =================

async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id != CHANNEL_ID:
        return

    if not update.message.reply_to_message:
        return

    if update.message.reply_to_message.message_id != current_battle.get("message_id"):
        return

    if update.message.text != "👍":
        return

    user_id = update.message.from_user.id

    if user_id == current_battle["p1"]:
        current_battle["v1"] += 1
    elif user_id == current_battle["p2"]:
        current_battle["v2"] += 1
    else:
        return

    cursor.execute("SELECT username FROM players WHERE user_id=?", (current_battle["p1"],))
    p1_name = cursor.fetchone()[0]

    cursor.execute("SELECT username FROM players WHERE user_id=?", (current_battle["p2"],))
    p2_name = cursor.fetchone()[0]

    new_text = (
        "🔥 <b>Битва Ников</b> 🔥\n\n"
        "🏆 Раунд: 1\n"
        "👥 Участников: 2\n\n"
        f"@{p1_name} VS @{p2_name}\n\n"
        "📊 Количество голосов:\n"
        f"Участник 1: {current_battle['v1']}\n"
        f"Участник 2: {current_battle['v2']}\n\n"
        "Голосовать 👍 (ответом на сообщение)"
    )

    await context.bot.edit_message_text(
        chat_id=CHANNEL_ID,
        message_id=current_battle["message_id"],
        text=new_text,
        parse_mode="HTML"
    )

# ================= ROUND LOGIC =================

async def next_round(context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("SELECT round FROM game WHERE id=1")
    current_round = cursor.fetchone()[0]

    requirement = ROUND_REQUIREMENTS.get(current_round, 0)

    cursor.execute(
        "UPDATE players SET alive=0 WHERE invited < ?",
        (requirement,)
    )

    cursor.execute("SELECT COUNT(*) FROM players WHERE alive=1")
    alive_count = cursor.fetchone()[0]

    if alive_count <= 1 or current_round >= 5:
        await finish_game(context)
        return

    cursor.execute("UPDATE game SET round = round + 1 WHERE id=1")
    conn.commit()

    context.job_queue.run_once(next_round, ROUND_TIME)

# ================= FINISH =================

async def finish_game(context):

    cursor.execute("""
        SELECT username, invited FROM players
        WHERE alive=1
        ORDER BY invited DESC
        LIMIT 1
    """)
    winner = cursor.fetchone()

    if winner:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"🏆 Победитель: {winner[0]}\n👥 Приглашено: {winner[1]}"
        )

    cursor.execute("DELETE FROM players")
    cursor.execute("DELETE FROM referrals")
    cursor.execute("UPDATE game SET round=1, active=0 WHERE id=1")
    conn.commit()

# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(join, pattern="join"))
    app.add_handler(CallbackQueryHandler(find_me, pattern="me"))
    app.add_handler(CallbackQueryHandler(rules, pattern="rules"))
    app.add_handler(CallbackQueryHandler(referral, pattern="ref"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, vote))

    app.job_queue.run_once(next_round, ROUND_TIME)
    app.job_queue.run_once(create_battle, 20)

    print("🚀 Production версия запущена")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
