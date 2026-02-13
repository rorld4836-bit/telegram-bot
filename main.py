import logging
import random
import asyncio
import pytz
from datetime import datetime, timedelta
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = "YOUR_TOKEN"
CHANNEL_ID = -1000000000000
BOT_USERNAME = "your_bot_username"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

conn = sqlite3.connect("battle.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    invited INTEGER DEFAULT 0,
    round INTEGER DEFAULT 1,
    active INTEGER DEFAULT 1
)
""")
conn.commit()

ROUND_TARGETS = {
    1: 10,
    2: 20,
    3: 30,
    4: 50
}

def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔥 Участвовать", callback_data="join"),
        InlineKeyboardButton("👥 Пригласить", callback_data="invite"),
        InlineKeyboardButton("📜 Правила", callback_data="rules")
    )
    return kb

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    args = message.get_args()
    user_id = message.from_user.id
    username = message.from_user.username or "NoName"

    cursor.execute("INSERT OR IGNORE INTO users(user_id, username) VALUES(?,?)",
                   (user_id, username))
    conn.commit()

    if args:
        inviter_id = int(args)
        if inviter_id != user_id:
            cursor.execute("UPDATE users SET invited = invited + 1 WHERE user_id=?",
                           (inviter_id,))
            conn.commit()

    await message.answer("Добро пожаловать в Битву Ников!", reply_markup=main_menu())

@dp.callback_query_handler(text="join")
async def join(callback: types.CallbackQuery):
    await callback.answer("Вы участвуете!")

@dp.callback_query_handler(text="invite")
async def invite(callback: types.CallbackQuery):
    link = f"https://t.me/{BOT_USERNAME}?start={callback.from_user.id}"
    await callback.message.edit_text(
        f"👥 Ваша ссылка:\n{link}\n\n"
        "Приглашай друзей и проходи раунды!",
        reply_markup=main_menu()
    )

@dp.callback_query_handler(text="rules")
async def rules(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📜 Правила:\n\n"
        "1. 4 раунда\n"
        "2. Побеждает тот, кто наберёт нужное количество приглашённых\n"
        "3. Накрутка = дисквалификация\n"
        "4. Всё проходит честно",
        reply_markup=main_menu()
    )

async def create_battle(round_number):
    cursor.execute("SELECT user_id, username, invited FROM users WHERE round=? AND active=1",
                   (round_number,))
    players = cursor.fetchall()

    if len(players) < 2:
        return

    p1, p2 = random.sample(players, 2)

    target = ROUND_TARGETS[round_number]

    moscow = pytz.timezone("Europe/Moscow")
    end_time = datetime.now(moscow) + timedelta(hours=2)
    end_time_str = end_time.strftime("%H:%M")

    text = (
        f"🔥 Битва Юзов\n"
        f"Раунд {round_number}\n\n"
        f"@{p1[1]} VS @{p2[1]}\n\n"
        f"1 игрок — {p1[2]}/{target} (пригласил)\n"
        f"2 игрок — {p2[2]}/{target} (пригласил)\n\n"
        f"Раунд закончится в {end_time_str} (МСК)"
    )

    await bot.send_message(CHANNEL_ID, text)

async def check_winners():
    while True:
        for round_number in range(1, 5):
            target = ROUND_TARGETS[round_number]
            cursor.execute("SELECT user_id FROM users WHERE round=? AND invited>=?",
                           (round_number, target))
            winners = cursor.fetchall()

            for winner in winners:
                if round_number < 4:
                    cursor.execute("UPDATE users SET round=? WHERE user_id=?",
                                   (round_number + 1, winner[0]))
                else:
                    cursor.execute("UPDATE users SET active=0 WHERE user_id=?",
                                   (winner[0]))
                    await bot.send_message(CHANNEL_ID,
                        f"🏆 Финальный победитель: @{winner[0]}")
                conn.commit()

        await asyncio.sleep(10)

async def on_startup(dp):
    asyncio.create_task(check_winners())

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
