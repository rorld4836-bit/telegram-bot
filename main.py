import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет!\n"
        "Я Telegram-бот, запущенный на Railway 🚀\n\n"
        "Напиши /help чтобы увидеть команды."
    )

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Доступные команды:\n\n"
        "/start — запустить бота\n"
        "/help — список команд\n"
        "/ping — проверить, жив ли бот\n"
        "/about — информация о боте"
    )

# /ping
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong! Бот работает 👍")

# /about
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Этот бот написан на Python\n"
        "☁️ Запущен в Railway\n"
        "📦 Использует python-telegram-bot v20+"
    )

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("about", about))

    print("🤖 Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
