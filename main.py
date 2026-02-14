import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ====== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ====== ДАННЫЕ (MVP, без БД) ======
users = {}
participants = []
matches = []
current_round = 1
registration_open = True

ROUND_TARGETS = {
    1: 5,
    2: 10,
    3: 20
}

# ====== /start ======
@dp.message(Command("start"))
async def start_handler(message: Message):
    args = message.text.split()
    user_id = message.from_user.id

    if user_id not in users:
        users[user_id] = {
            "invites": 0,
            "invited_by": None,
            "round_invites": 0,
            "status": "none"
        }

    # реферальная система
    if len(args) > 1:
        try:
            inviter = int(args[1])
            if inviter != user_id and inviter in users:
                users[user_id]["invited_by"] = inviter
                users[inviter]["invites"] += 1
                users[inviter]["round_invites"] += 1
                await check_winner(inviter)
        except:
            pass

    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={user_id}"

    await message.answer(
        f"🔥 Битва Юзов!\n\n"
        f"Твоя ссылка:\n{link}\n\n"
        f"/participate — участвовать"
    )

# ====== /participate ======
@dp.message(Command("participate"))
async def participate_handler(message: Message):
    global registration_open

    if not registration_open:
        await message.answer("❌ Регистрация закрыта (идёт 2 раунд)")
        return

    user_id = message.from_user.id

    if user_id not in participants:
        participants.append(user_id)
        users[user_id]["status"] = "waiting"
        await message.answer("✅ Ты участвуешь в турнире!")
        await try_create_match()

# ====== СОЗДАНИЕ МАТЧЕЙ ======
async def try_create_match():
    waiting = [u for u in participants if users[u]["status"] == "waiting"]

    if len(waiting) >= 2:
        p1 = waiting[0]
        p2 = waiting[1]

        users[p1]["status"] = "fighting"
        users[p2]["status"] = "fighting"

        matches.append((p1, p2, current_round))

        await post_match(p1, p2)

async def post_match(p1, p2):
    text = (
        f"⚔ Раунд {current_round}\n"
        f"До {ROUND_TARGETS[current_round]} приглашённых\n\n"
        f"{p1}: 0/{ROUND_TARGETS[current_round]}\n"
        f"🆚\n"
        f"{p2}: 0/{ROUND_TARGETS[current_round]}"
    )

    await bot.send_message(CHANNEL_ID, text)

# ====== ПРОВЕРКА ПОБЕДЫ ======
async def check_winner(user_id):
    global current_round, registration_open

    if users[user_id]["round_invites"] >= ROUND_TARGETS[current_round]:

        users[user_id]["status"] = "advanced"
        users[user_id]["round_invites"] = 0

        await bot.send_message(
            CHANNEL_ID,
            f"🏆 {user_id} проходит в следующий раунд!"
        )

        if current_round == 1:
            current_round = 2
            registration_open = False
            await bot.send_message(CHANNEL_ID, "🔒 Регистрация закрыта!")

        elif current_round == 2:
            current_round = 3

        elif current_round == 3:
            await bot.send_message(
                CHANNEL_ID,
                f"👑 {user_id} ПОБЕДИТЕЛЬ ТУРНИРА!"
            )

# ====== АВТОСТАРТ ТУРНИРА ======
async def start_tournament():
    global current_round, registration_open
    current_round = 1
    registration_open = True
    await bot.send_message(CHANNEL_ID, "🔥 Новый турнир начался!")

scheduler = AsyncIOScheduler()
scheduler.add_job(start_tournament, "interval", hours=24)
scheduler.start()

# ====== ЗАПУСК ======
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
