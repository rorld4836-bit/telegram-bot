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

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_LINK = "https://t.me/battlertf"
CHANNEL_ID = -100XXXXXXXXXX  # вставь id канала
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
        f"""
📜 <b>ПРАВИЛА ТУРНИРА</b>

1️⃣ Каждый участник получает личную ссылку.
1 приглашённый = 1 участник турнира.

2️⃣ Один человек может быть засчитан только один раз.
Самоприглашение запрещено.

3️⃣ Все участники находятся в равных условиях.
Кто пригласил больше людей — тот выше в рейтинге.

4️⃣ Турнир проходит в 4 раунда:
Раунд 1 — без ограничений  
Раунд 2 — минимум 10 приглашений  
Раунд 3 — минимум 20 приглашений  
Раунд 4 — минимум 30 приглашений  

5️⃣ После 4 раунда определяется один победитель —
участник с наибольшим количеством приглашений.

🏆 Награда:
В конце турнира победитель получает подарок звёзд ⭐
(примерно от 50 до 500 ⭐).
Размер награды зависит от вашей активности.

🔒 Все данные используются только внутри турнира.
Бот не запрашивает пароли, коды или личные данные.
Участие полностью безопасно.

Битвы проходят здесь:
{CHANNEL_LINK}
""",
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

        text = (
            "🔥 <b>БИТВА НИКОВ</b> 🔥\n\n"
            f"🏆 Раунд: {round_num}\n"
            "👥 Участников: 2\n\n"
            f"@{u1[0]} VS @{u2[0]}\n\n"
            "📊 Количество приглашений:\n"
            f"Участник 1: {u1[1]}\n"
            f"Участник 2: {u2[1]}\n\n"
            "Голосовать 👍\n\n"
            f"Канал турнира:\n{CHANNEL_LINK}"
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

# ================= ROUND =================

async def next_round(context: ContextTypes.DEFAULT_TYPE):

    cursor.execute("SELECT round FROM game WHERE id=1")
    current = cursor.fetchone()[0]

    requirement = ROUND_REQUIREMENTS.get(current, 0)

    cursor.execute("UPDATE players SET alive=0 WHERE invited < ?", (requirement,))
    cursor.execute("UPDATE game SET round = round + 1 WHERE id=1")
    conn.commit()

    if current >= 4:
        await finish(context)
        return

    context.job_queue.run_once(next_round, ROUND_TIME)

# ================= FINISH =================

async def finish(context):

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
            text=f"🏆 ПОБЕДИТЕЛЬ ТУРНИРА:\n\n@{winner[0]}\nПриглашено: {winner[1]}"
        )

# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(rules, pattern="rules"))

    app.job_queue.run_repeating(create_battle, 600)
    app.job_queue.run_once(next_round, ROUND_TIME)

    print("🔥 Турнирный бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
