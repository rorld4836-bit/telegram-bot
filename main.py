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
CHANNEL_LINK = "https://t.me/battlertf"
ADMIN_ID = 6885494136

ROUND_TARGETS = {1: 5, 2: 10, 3: 20}
MSK = pytz.timezone("Europe/Moscow")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

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
    is_pro = Column(Boolean, default=True)


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
    opponent_id = Column(BigInteger, nullable=True)

# ================= INIT =================

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ================= KEYBOARD =================

def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Участвовать", callback_data="participate")],
        [InlineKeyboardButton(text="📨 Пригласить", callback_data="invite")],
        [InlineKeyboardButton(text="📖 Правила", callback_data="rules")],
        [InlineKeyboardButton(text="📢 Канал", url=CHANNEL_LINK)]
    ])

# ================= START =================

@dp.message(Command("start"))
async def start_handler(message: Message):
    user_id = message.from_user.id
    args = message.text.split()

    async with SessionLocal() as session:
        user = await session.get(User, user_id)

        if not user:
            invited_by = None

            if len(args) > 1:
                try:
                    invited_by = int(args[1])
                except:
                    pass

            user = User(id=user_id, invited_by=invited_by)
            session.add(user)

            if invited_by:
                inviter = await session.get(User, invited_by)
                if inviter:
                    inviter.total_invites += 1

                    result = await session.execute(
                        select(Participant).where(
                            Participant.user_id == invited_by
                        )
                    )
                    participant = result.scalars().first()
                    if participant:
                        participant.round_invites += 1

            await session.commit()

    await message.answer(
        "🔥 Добро пожаловать в Битву Юзов!\n\n"
        "Приглашай друзей и побеждай!",
        reply_markup=main_keyboard()
    )

# ================= PARTICIPATE =================

@dp.callback_query(F.data == "participate")
async def participate(callback):
    user_id = callback.from_user.id

    async with SessionLocal() as session:
        result = await session.execute(
            select(Tournament).where(Tournament.active == True)
        )
        tournament = result.scalars().first()

        if not tournament:
            await callback.message.answer("❌ Турнир не активен")
            return

        # Проверка — уже участвует в этом раунде
        result = await session.execute(
            select(Participant).where(
                Participant.user_id == user_id,
                Participant.round_number == tournament.current_round
            )
        )
        existing = result.scalars().first()

        if existing:
            await callback.message.answer("⚠️ Ты уже участвуешь в этом раунде!")
            return

        participant = Participant(
            user_id=user_id,
            round_number=tournament.current_round
        )
        session.add(participant)
        await session.commit()

        await callback.message.answer("✅ Ты участвуешь!")

# ================= INVITE =================

@dp.callback_query(F.data == "invite")
async def invite(callback):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={callback.from_user.id}"
    await callback.message.answer(f"📨 Твоя ссылка:\n{link}")

# ================= RULES =================

@dp.callback_query(F.data == "rules")
async def rules(callback):
    await callback.message.answer(
        "📖 Правила:\n\n"
        "1. Приглашай людей через свою ссылку\n"
        "2. Кто больше пригласит — проходит дальше\n"
        "3. Раунд завершается автоматически в 14:00 МСК\n"
        "4. Минимум 2 участника для старта раунда"
    )

# ================= ROUND LOGIC =================

async def finish_round():
    async with SessionLocal() as session:
        result = await session.execute(
            select(Tournament).where(Tournament.active == True)
        )
        tournament = result.scalars().first()

        if not tournament:
            return

        result = await session.execute(
            select(Participant).where(
                Participant.round_number == tournament.current_round
            )
        )
        players = result.scalars().all()

        # 🔥 минимум 2 участника
        if len(players) < 2:
            await bot.send_message(
                CHANNEL_ID,
                f"⚠️ Раунд {tournament.current_round} не может завершиться.\n"
                f"Недостаточно участников (минимум 2)."
            )
            return

        players = sorted(players, key=lambda x: x.round_invites, reverse=True)
        winner = players[0]

        await bot.send_message(
            CHANNEL_ID,
            f"👑 Раунд {tournament.current_round} завершён!\n\n"
            f"🏆 Победитель: {winner.user_id}\n"
            f"📨 Приглашений: {winner.round_invites}"
        )

        # авто-переключение
        tournament.current_round += 1
        await session.commit()

        await bot.send_message(
            CHANNEL_ID,
            f"🚀 Начался раунд {tournament.current_round}!\n"
            f"Нажмите «Участвовать», чтобы вступить."
        )

# ================= ADMIN =================

@dp.message(Command("start_tournament"))
async def start_tournament(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    async with SessionLocal() as session:
        t = Tournament()
        session.add(t)
        await session.commit()

    await message.answer("🚀 Турнир создан!")

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

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
