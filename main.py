import logging
import random
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = "PASTE_YOUR_BOT_TOKEN"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ================= DATABASE =================

conn = sqlite3.connect("battle.db")
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

conn.commit()

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

    cursor.execute("INSERT OR IGNORE INTO users(user_id, username) VALUES(?,?)",
                   (user_id, username))
    conn.commit()

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
        f"🎤 Голосов: {data[1]}\n"
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
        "✅ Вы участвуете в Битве Ников!\n\n"
        "Ожидайте начала раунда.",
        reply_markup=main_menu()
    )

# ================= REFERRAL =================

@dp.callback_query_handler(lambda c: c.data == "ref")
async def ref(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    link = f"https://t.me/YOUR_BOT_USERNAME?start={user_id}"

    await callback.message.edit_text(
        f"📢 Ваша реферальная ссылка:\n\n{link}\n\n"
        "За каждого приглашенного вы получаете +1 голос.",
        reply_markup=main_menu()
    )

# ================= RULES =================

@dp.callback_query_handler(lambda c: c.data == "rules")
async def rules(callback: types.CallbackQuery):
    text = """
📜 Правила участия в «Битве ников»

1️⃣ Участвуют все зарегистрированные участники.
2️⃣ Подтвердите участие через кнопку «Участвовать».
3️⃣ Ники с оскорблениями запрещены.
4️⃣ Битва проходит в 4 раунда.
5️⃣ Победитель определяется голосованием.
6️⃣ Накрутка голосов = дисквалификация.
7️⃣ Личные данные не сохраняются.
"""
    await callback.message.edit_text(text, reply_markup=main_menu())

# ================= START BATTLE =================

@dp.message_handler(commands=["battle"])
async def start_battle(message: types.Message):
    cursor.execute("SELECT user_id, username FROM users WHERE registered=1")
    players = cursor.fetchall()

    if len(players) < 2:
        await message.answer("Недостаточно участников.")
        return

    p1, p2 = random.sample(players, 2)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(p1[1] or "NoName", callback_data=f"vote_{p1[0]}"),
        InlineKeyboardButton(p2[1] or "NoName", callback_data=f"vote_{p2[0]}")
    )

    await message.answer(
        "🔥 Битва ников!\n\nВыберите лучший ник:",
        reply_markup=kb
    )

# ================= VOTE =================

@dp.callback_query_handler(lambda c: c.data.startswith("vote_"))
async def vote(callback: types.CallbackQuery):
    winner_id = int(callback.data.split("_")[1])

    cursor.execute("UPDATE users SET votes=votes+1 WHERE user_id=?",
                   (winner_id,))
    conn.commit()

    await callback.answer("Голос засчитан!")

# ================= RUN =================

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
