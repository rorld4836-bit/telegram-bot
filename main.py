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

print("БОТ ЗАПУЩЕН")

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("❌ BOT_TOKEN не найден!")
    exit()

CHANNEL_LINK = "https://t.me/battlertf"
CHANNEL_ID = -1003814033445

ROUND_TIME = 7 * 60 * 60
UPDATE_TIME = 30
CREATE_BATTLE_INTERVAL = 600

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
    active INTEGER DEFAULT 1,
    winner INTEGER DEFAULT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS game (
    id INTEGER PRIMARY KEY,
    round INTEGER DEFAULT 1
)
""")

cursor.execute("INSERT OR IGNORE INTO game (id, round) VALUES (1,1)")

cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_alive ON players(alive)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_battles_active ON battles(active)")

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

    cursor.execute(
        "INSERT OR IGNORE INTO players (user_id, username) VALUES (?,?)",
        (user.id, user.username)
    )
    conn.commit()

    if args:
        try:
            ref_id = int(args[0])
            if ref_id != user.id:
                cursor.execute("SELECT 1 FROM referrals WHERE invited_id=?", (user.id,))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO referrals VALUES (?,?)", (ref_id, user.id))
                    cursor.execute(
                        "UPDATE players SET invited=invited+1 WHERE user_id=?",
                        (ref_id,)
                    )
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
        f"📜 <b>ПРАВИЛА</b>\n\n"
        f"• Учитываются приглашения\n"
        f"• Победитель один\n"
        f"• 4 раунда\n"
        f"• Награда: 50–500 ⭐ (зависит от активности)\n\n"
        f"Битвы проходят здесь:\n{CHANNEL_LINK}",
        parse_mode="HTML"
    )

# ================= CREATE BATTLE =================

async def create_battle(context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("SELECT COUNT(*) FROM battles WHERE active=1")
    active_count = cursor.fetchone()[0]

    # защита от перегрузки (макс 10 параллельных битв)
    if active_count >= 10:
        return

    cursor.execute("SELECT user_id FROM players WHERE alive=1")
    players = [x[0] for x in cursor.fetchall()]

    if len(players) < 2:
        return

    p1, p2 = random.sample(players, 2)

    msg = await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text="⏳ Создание битвы..."
    )

    cursor.execute(
        "INSERT INTO battles (p1, p2, message_id) VALUES (?,?,?)",
        (p1, p2, msg.message_id)
    )
    conn.commit()

# ================= UPDATE BATTLES =================

async def update_battles(context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("SELECT round FROM game WHERE id=1")
    round_num = cursor.fetchone()[0]

    cursor.execute("SELECT id, p1, p2, message_id FROM battles WHERE active=1")
    battles = cursor.fetchall()

    for battle in battles:
        b_id, p1, p2, message_id = battle

        cursor.execute("SELECT username, invited FROM players WHERE user_id=?", (p1,))
        u1 = cursor.fetchone()

        cursor.execute("SELECT username, invited FROM players WHERE user_id=?", (p2,))
        u2 = cursor.fetchone()

        if not u1 or not u2:
            continue

        # Определение победителя после 4 раунда
        if round_num >= 4:
            if u1[1] > u2[1]:
                winner = p1
            elif u2[1] > u1[1]:
                winner = p2
            else:
                winner = random.choice([p1, p2])

            cursor.execute(
                "UPDATE battles SET active=0, winner=? WHERE id=?",
                (winner, b_id)
            )
            conn.commit()

            winner_username = u1[0] if winner == p1 else u2[0]

            text = (
                "🏆 <b>БИТВА ЗАВЕРШЕНА</b>\n\n"
                f"Победитель: @{winner_username}\n\n"
                "Награда: 50–500 ⭐"
            )
        else:
            text = (
                "🔥 <b>БИТВА НИКОВ</b> 🔥\n\n"
                f"🏆 Раунд: {round_num}\n\n"
                f"@{u1[0]} VS @{u2[0]}\n\n"
                f"📊 Приглашения:\n"
                f"{u1[0]}: {u1[1]}\n"
                f"{u2[0]}: {u2[1]}\n\n"
                f"Канал: {CHANNEL_LINK}"
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

# ================= MAIN =================

def main():
    print("БОТ ЗАПУЩЕН")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(rules, pattern="rules"))

    # создание битв
    app.job_queue.run_repeating(create_battle, CREATE_BATTLE_INTERVAL)

    # обновление (ОДИН раз, без зацикливания)
    app.job_queue.run_repeating(update_battles, UPDATE_TIME)

    app.run_polling()

if __name__ == "__main__":
    main()
