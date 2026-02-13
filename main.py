import logging
import random
import sqlite3
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

# ===== TOKEN FROM RAILWAY =====
API_TOKEN = os.getenv("API_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")

if not API_TOKEN:
    raise ValueError("API_TOKEN не найден! Добавь его в Railway Variables.")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ================= DATABASE =================

conn = sqlite3.connect("battle.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    registered INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    votes INTEGER DEFAULT 0,
    invited INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS votes(
    voter_id INTEGER,
    round_id INTEGER
)
""")

conn.commit()

current_round = 0
current_players = []

# ================= KEYBOARDS =================

def main_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔥 Участвовать", callback_data="join"))
    kb.add(InlineKeyboardButton("👤 Профиль", callback_data="profile"))
    kb.add(InlineKeyboardButton("📢 Пригласить друзей", callback_data="ref"))
    kb.add(InlineKeyboardButton("📜 Правила", callback_data="rules"))
    return kb

# ================= START =================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    args = message.get_args()

    cursor.execute("INSERT OR IGNORE INTO users(user_id, username) VALUES(?,?)",
                   (user_id, username))
    conn.commit()

    # ===== Referral =====
    if args:
        try:
            inviter_id = int(args)
            if inviter_id != user_id:
                cursor.execute("UPDATE users SET invited=invited+1 WHERE user_id=?",
                               (inviter_id,))
                conn.commit()
        except:
            pass

    await message.answer(
        "🎮 Добро пожаловать в Битву Ников!\n\nВыберите действие:",
        reply_markup=main_menu()
    )

# ================= PROFILE =================

@dp.callback_query_handler(lambda c: c.data == "profile")
async def profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    cursor.execute("SELECT wins, votes, invited FROM users WHERE user_id=?",
                   (user_id,))
    data = cursor.fetchone()

    await callback.message.edit_text(
        f"👤 Ваш профиль\n\n"
        f"🏆 Побед: {data[0]}\n"
        f"🎤 Голосов получено: {data[1]}\n"
        f"👥 Приглашено: {data[2]}",
        reply_markup=main_menu()
    )

# ================= JOIN =================

@dp.callback_query_handler(lambda c: c.data == "join")
async def join(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    cursor.execute("UPDATE users SET registered=1 WHERE user_id=?",
                   (user_id,))
    conn.commit()

    await callback.answer("Вы зарегистрированы!")
    await callback.message.edit_text(
        "✅ Вы участвуете в Битве Ников!\n\nОжидайте начала раунда.",
        reply_markup=main_menu()
    )

# ================= REF =================

@dp.callback_query_handler(lambda c: c.data == "ref")
async def ref(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if not BOT_USERNAME:
        link = "Добавь BOT_USERNAME в Railway Variables"
    else:
        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

    await callback.message.edit_text(
        f"📢 Ваша реферальная ссылка:\n\n{link}\n\n"
        "За каждого приглашенного вы получаете +1 приглашение.",
        reply_markup=main_menu()
    )

# ================= RULES =================

@dp.callback_query_handler(lambda c: c.data == "rules")
async def rules(callback: types.CallbackQuery):
    text = """
📜 Правила участия

1️⃣ Участвуют зарегистрированные.
2️⃣ Подтвердите участие.
3️⃣ Оскорбления запрещены.
4️⃣ Битва — 4 раунда.
5️⃣ Победитель — по голосам.
6️⃣ Накрутка = дисквалификация.
"""
    await callback.message.edit_text(text, reply_markup=main_menu())

# ================= START BATTLE =================

@dp.message_handler(commands=["battle"])
async def start_battle(message: types.Message):
    global current_round, current_players

    cursor.execute("SELECT user_id, username FROM users WHERE registered=1")
    players = cursor.fetchall()

    if len(players) < 2:
        await message.answer("Недостаточно участников.")
        return

    current_round += 1
    current_players = random.sample(players, 2)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(current_players[0][1] or "NoName",
                             callback_data=f"vote_{current_players[0][0]}"),
        InlineKeyboardButton(current_players[1][1] or "NoName",
                             callback_data=f"vote_{current_players[1][0]}")
    )

    await message.answer(
        f"🔥 Раунд {current_round}\n\nВыберите лучший ник:",
        reply_markup=kb
    )

# ================= VOTE =================

@dp.callback_query_handler(lambda c: c.data.startswith("vote_"))
async def vote(callback: types.CallbackQuery):
    global current_round

    voter_id = callback.from_user.id
    winner_id = int(callback.data.split("_")[1])

    # Проверка на повторное голосование
    cursor.execute("SELECT * FROM votes WHERE voter_id=? AND round_id=?",
                   (voter_id, current_round))
    if cursor.fetchone():
        await callback.answer("Вы уже голосовали!", show_alert=True)
        return

    cursor.execute("INSERT INTO votes(voter_id, round_id) VALUES(?,?)",
                   (voter_id, current_round))
    cursor.execute("UPDATE users SET votes=votes+1 WHERE user_id=?",
                   (winner_id,))
    conn.commit()

    await callback.answer("Голос засчитан!")

# ================= RUN =================

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
