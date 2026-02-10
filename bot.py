import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler
from config import TOKEN
from handlers import start
from database import engine
from models import Base

async def main():
    Base.metadata.create_all(bind=engine)

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    print("🤖 Бот запущен")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
