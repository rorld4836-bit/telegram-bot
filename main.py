import os
import asyncio
import pytz
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, select

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

CHANNEL_ID = -1003814033445
ADMIN_ID = 123456789  # <-- вставь свой id
ROUND_TARGETS = {1: 5, 2: 10, 3: 20}

MSK = pytz.timezone("Europe/Moscow")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql+asyncpg://"
    )

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# ================= MODELS =================

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    invited_by = Column(BigInteger, nullable=True)
    total_invites = Column(Integer, default=0)
    is_pro = Column(Boolean, default=False)


class Tournament(Base):
    __tablename__ = "tournament"

    id = Column(Integer, primary_key=True)
    current_round = Column(Integer, default=1)
    registration_open = Column(Boolean, default=True)
    active = Column(Boolean, default=True)


class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger)
    round_number = Column(Integer)
    round_invites = Column(Integer, default=0)
    status = Column(String, default="waiting")
    opponent_id = Column(BigInteger, nullable=True)

# ================= DB INIT =================

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ================= TOURNAMENT LOGIC =================

async def get_active_tournament(session):
    result = await session.execute(
        select(Tournament).where(Tournament.active == True)
    )
    return result.scalars().first()

async def generate_pairs(tournament):
    async with SessionLocal() as session:
        result = await session.execute(
            select(Participant).where(
                Participant.round_number == tournament.current_round,
                Participant.opponent_id == None
            )
        )

        players = result.scalars().all()

        for i in range(0, len(players), 2):
            if i + 1 < len(players):
                p1 = players[i]
                p2 = players[i + 1]

                p1.opponent_id = p2.user_id
                p2.opponent_id = p1.user_id

                await bot.send_message(
                    CHANNEL_ID,
                    f"🔥 Битва Юзов\n\n"
                    f"Раунд {tournament.current_round}\n\n"
                    f"{p1.user_id} VS {p2.user_id}\n\n"
                    f"Количество приглашений\n"
                    f"1 игрок — 0/{ROUND_TARGETS[tournament.current_round]}\n"
                    f"2 игрок — 0/{ROUND_TARGETS[tournament.current_round]}\n\n"
                    f"Итог раунда в 14:00 по МСК времени"
                )

        await session.commit()

async def finish_round():
    async with SessionLocal() as session:
        tournament = await get_active_tournament(session)
        if not tournament:
            return

        result = await session.execute(
            select(Participant).where(
                Participant.round_number == tournament.current_round
            )
        )

        players = result.scalars().all()
        winners = []
        processed = set()

        for p in players:
            if p.user_id in processed:
                continue

            opponent = await session.execute(
                select(Participant).where(
                    Participant.user_id == p.opponent_id,
                    Participant.round_number == tournament.current_round
                )
            )

            opponent = opponent.scalars().first()
            if not opponent:
                continue

            if p.round_invites >= opponent.round_invites:
                winners.append(p.user_id)
            else:
                winners.append(opponent.user_id)

            processed.add(p.user_id)
            processed.add(opponent.user_id)

        # ФИНАЛ
        if len(winners) == 1:
            await bot.send_message(
                CHANNEL_ID,
                f"👑 ФИНАЛ ТУРНИРА 👑\n\n"
                f"Победитель: {winners[0]}\n\n"
                f"🏆 Абсолютный чемпион Битвы Юзов!"
            )

            tournament.active = False
            await session.commit()
            return

        # следующий раунд
        tournament.current_round += 1

        for user_id in winners:
            new_participant = Participant(
                user_id=user_id,
                round_number=tournament.current_round
            )
            session.add(new_participant)

        await session.commit()
        await generate_pairs(tournament)

async def create_tournament():
    async with SessionLocal() as session:
        t = Tournament()
        session.add(t)
        await session.commit()
        await generate_pairs(t)

# ================= HANDLERS =================

def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Участвовать", callback_data="participate")],
        [InlineKeyboardButton(text="📨 Пригласить", callback_data="invite")],
        [InlineKeyboardButton(text="📖 Правила", callback_data="rules")],
        [InlineKeyboardButton(text="📢 Канал", url="https://t.me/yourchannel")]
    ])

@dp.message(Command("start"))
async def start_handler(message: Message):
    user_id = message.from_user.id
    args = message.text.split()

    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            user = User(id=user_id)
            session.add(user)
            await session.commit()

    await message.answer(
        "🔥 Добро пожаловать в Битву Юзов!",
        reply_markup=main_keyboard()
    )

@dp.callback_query(F.data == "rules")
async def rules(callback):
    await callback.message.answer(
        "📖 Правила:\n"
        "1. Приглашай людей.\n"
        "2. Кто больше — тот проходит дальше.\n"
        "3. Итог в 14:00 МСК."
    )

@dp.callback_query(F.data == "invite")
async def invite(callback):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={callback.from_user.id}"
    await callback.message.answer(f"📨 Твоя ссылка:\n{link}")

@dp.callback_query(F.data == "participate")
async def participate(callback):
    user_id = callback.from_user.id

    async with SessionLocal() as session:
        tournament = await get_active_tournament(session)
        user = await session.get(User, user_id)

        if not user.is_pro:
            await callback.message.answer(
                "💎 Только PRO игроки могут участвовать."
            )
            return

        if not tournament or not tournament.registration_open:
            await callback.message.answer("❌ Регистрация закрыта")
            return

        participant = Participant(
            user_id=user_id,
            round_number=tournament.current_round
        )

        session.add(participant)
        await session.commit()

        await callback.message.answer("✅ Ты участвуешь!")

# ================= ADMIN =================

@dp.message(Command("give_pro"))
async def give_pro(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        user_id = int(message.text.split()[1])
    except:
        await message.answer("Используй: /give_pro user_id")
        return

    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user:
            user.is_pro = True
            await session.commit()
            await message.answer("PRO выдан.")

# ================= MAIN =================

async def main():
    await init_db()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        finish_round,
        "cron",
        hour=14,
        minute=0,
        timezone=MSK
    )
    scheduler.start()

    await create_tournament()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
