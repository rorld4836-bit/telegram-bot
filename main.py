import os
import sqlite3
import random
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

print("БОТ ЗАПУЩЕН")  # ← проверка старта

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("❌ BOT_TOKEN не найден!")
    exit()

CHANNEL_LINK = "https://t.me/battlertf"
CHANNEL_ID = -100XXXXXXXXXX  # вставь реальный id
ROUND_TIME = 7 * 60 * 60
UPDATE_TIME = 30

ROUND_REQUIREMENTS = {
    1: 0,
    2: 10,
    3: 20,
    4: 30
}

logging.basicConfig(level=logging.INFO)

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
CREATE TABLE IF NOT EXISTS battles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    p1 INTEGER,
    p2 INTEGER,
    message_id INTEGER,
    active INTEGER DEFAULT 1
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS game (
    id INTEGER PRIMARY KEY,
    round INTEGER DEFAULT 1
)
""")

cursor.execute("INSERT OR IGNORE INTO game (id, round) VALUES (1,1)")
conn.commit()

# ================= MENU =================

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Участвовать", callback_data="join")],
        [InlineKeyboardButton("👤 Профиль", callback_data="me")],
        [InlineKeyboardButton("📜 Правила", callback_data="rules")],
        [InlineKeyboardButton("📩 Пригласить", callback_data="ref")]
    ])

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    cursor.execute("INSERT OR IGNORE INTO players (user_id, username) VALUES (?,?)",
                   (user.id, user.username))
    conn.commit()

    if args:
        try:
            ref_id = int(args[0])
            if ref_id != user.id:
                cursor.execute("SELECT 1 FROM referrals WHERE invited_id=?", (user.id,))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO referrals VALUES (?,?)", (ref_id, user.id))
                    cursor.execute("UPDATE players SET invited=invited+1 WHERE user_id=?", (ref_id,))
                    conn.commit()
        except:
            pass

    await update.message.reply_text(
        "🔥 <b>БИТВА НИКОВ</b> 🔥\n\n"
        f"Битвы проходят здесь:\n{CHANNEL_LINK}\n\n"
        "Выберите действие 👇",
        parse_mode="HTML",
        reply_markup=menu()
    )

# ================= RULES =================

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        f"📜 <b>ПРАВИЛА ТУРНИРА</b>\n\n"
        f"Битвы проходят здесь:\n{CHANNEL_LINK}",
        parse_mode="HTML"
    )

# ================= CREATE BATTLE =================

async def create_battle(context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("SELECT user_id FROM players WHERE alive=1")
    players = [x[0] for x in cursor.fetchall()]

    if len(players) < 2:
        return

    p1, p2 = random.sample(players, 2)

    msg = await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text="⏳ Загрузка битвы..."
    )

    cursor.execute(
        "INSERT INTO battles (p1, p2, message_id) VALUES (?,?,?)",
        (p1, p2, msg.message_id)
    )
    conn.commit()

    context.job_queue.run_repeating(update_battle, UPDATE_TIME)

# ================= UPDATE BATTLE =================

async def update_battle(context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("SELECT id, p1, p2, message_id FROM battles WHERE active=1")
    battles = cursor.fetchall()

    cursor.execute("SELECT round FROM game WHERE id=1")
    round_num = cursor.fetchone()[0]

    for battle in battles:
        b_id, p1, p2, message_id = battle

        cursor.execute("SELECT username, invited FROM players WHERE user_id=?", (p1,))
        u1 = cursor.fetchone()

        cursor.execute("SELECT username, invited FROM players WHERE user_id=?", (p2,))
        u2 = cursor.fetchone()

        if not u1 or not u2:
            continue

        text = (
            "🔥 <b>БИТВА НИКОВ</b> 🔥\n\n"
            f"🏆 Раунд: {round_num}\n\n"
            f"@{u1[0]} VS @{u2[0]}\n\n"
            f"Приглашено: {u1[1]} vs {u2[1]}"
        )

        try:
            await context.bot.edit_message_text(
                chat_id=CHANNEL_ID,
                message_id=message_id,
                text=text,
                parse_mode="HTML"
            )
        except:
            pass

# ================= FINISH =================

async def finish(context: ContextTypes.DEFAULT_TYPE):

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
            text=f"🏆 ПОБЕДИТЕЛЬ:\n\n@{winner[0]}\nПриглашено: {winner[1]}"
        )

# ================= MAIN =================

def main():
    print("БОТ ЗАПУЩЕН")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(rules, pattern="rules"))

    app.job_queue.run_repeating(create_battle, 600)

    app.run_polling()

if __name__ == "__main__":
    main()
