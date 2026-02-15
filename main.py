import os
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, select

# =========================
# CONFIG
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# =========================
# DATABASE MODELS
# =========================

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    invited_by = Column(BigInteger, nullable=True)
    total_invites = Column(Integer, default=0)


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
    status = Column(String, default="waiting")  # waiting, fighting, eliminated, advanced


ROUND_TARGETS = {1: 5, 2: 10, 3: 20}

# =========================
# DATABASE INIT
# =========================

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# =========================
# TOURNAMENT LOGIC
# =========================

async def get_active_tournament(session):
    result = await session.execute(select(Tournament).where(Tournament.active == True))
    return result.scalars().first()


async def create_tournament():
    async with SessionLocal() as session:
        t = Tournament()
        session.add(t)
        await session.commit()
        await bot.send_message(CHANNEL_ID, "🔥 Новый турнир начался!")


async def check_winner(session, participant, tournament):
    target = ROUND_TARGETS[tournament.current_round]

    if participant.round_invites >= target:
        participant.status = "advanced"
        participant.round_invites = 0

        await bot.send_message(
            CHANNEL_ID,
            f"🏆 {participant.user_id} прошёл раунд {tournament.current_round}"
        )

        await session.commit()

        # переход раунда
        if tournament.current_round == 1:
            tournament.current_round = 2
            tournament.registration_open = False
            await bot.send_message(CHANNEL_ID, "🔒 Регистрация закрыта!")

        elif tournament.current_round == 2:
            tournament.current_round = 3

        elif tournament.current_round == 3:
            await bot.send_message(
                CHANNEL_ID,
                f"👑 {participant.user_id} ПОБЕДИТЕЛЬ ТУРНИРА!"
            )
            tournament.active = False

        await session.commit()

# =========================
# HANDLERS
# =========================

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

        # реферал
        if len(args) > 1:
            try:
                inviter_id = int(args[1])
                if inviter_id != user_id:
                    inviter = await session.get(User, inviter_id)
                    if inviter:
                        user.invited_by = inviter_id
                        inviter.total_invites += 1

                        # добавляем в текущий раунд
                        tournament = await get_active_tournament(session)
                        if tournament:
                            result = await session.execute(
                                select(Participant).where(
                                    Participant.user_id == inviter_id,
                                    Participant.round_number == tournament.current_round
                                )
                            )
                            participant = result.scalars().first()
                            if participant:
                                participant.round_invites += 1
                                await check_winner(session, participant, tournament)

                        await session.commit()
            except:
                pass

    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={user_id}"

    await message.answer(
        f"🔥 Битва Юзов\n\n"
        f"Твоя ссылка:\n{link}\n\n"
        f"/participate — участвовать"
    )


@dp.message(Command("participate"))
async def participate_handler(message: Message):
    user_id = message.from_user.id

    async with SessionLocal() as session:
        tournament = await get_active_tournament(session)

        if not tournament or not tournament.registration_open:
            await message.answer("❌ Регистрация закрыта")
            return

        participant = Participant(
            user_id=user_id,
            round_number=tournament.current_round
        )

        session.add(participant)
        await session.commit()

        await message.answer("✅ Ты участвуешь в турнире!")

# =========================
# AUTO START
# =========================

scheduler = AsyncIOScheduler()
scheduler.add_job(create_tournament, "interval", hours=24)
scheduler.start()

# =========================
# MAIN
# =========================

async def main():
    await init_db()
    await create_tournament()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
