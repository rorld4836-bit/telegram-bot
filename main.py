import os
import logging
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -1003814033445
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
        "🔥 <b>БИТВА НИКОВ</b> 🔥\n\nДобро пожаловать!\n\nВыбери действие 👇",
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

    app.job_queue.run_once(next_round, ROUND_TIME)

    print("🚀 Production версия запущена")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
