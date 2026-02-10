import asyncio
import random
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

TOKEN = "ТВОЙ_ТОКЕН_ОТ_BOTFATHER"

# ====== ХРАНИЛИЩЕ ДАННЫХ (пока в памяти) ======
players = set()
battle_active = False


# ====== КОМАНДЫ ======

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет!\n"
        "Это 🤖 Battle Bot — битва ников ⚔️\n\n"
        "Команды:\n"
        "/join — войти в битву\n"
        "/battle — начать битву\n"
        "/help — помощь"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 Команды бота:\n"
        "/start — запуск\n"
        "/join — участвовать в битве\n"
        "/battle — начать битву\n"
        "/ping — проверить бота\n"
        "/about — о боте"
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong! Бот жив.")


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Battle Bot\n"
        "Первая версия\n"
        "Запущен на Railway 🚀"
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global players, battle_active

    if battle_active:
        await update.message.reply_text("⚠️ Битва уже идёт. Подожди следующую.")
        return

    user = update.effective_user.username
    if not user:
        await update.message.reply_text("❌ У тебя нет username в Telegram.")
        return

    players.add(user)
    await update.message.reply_text(
        f"✅ @{user} вошёл в битву!\n"
        f"👥 Участников: {len(players)}"
    )


async def battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global players, battle_active

    if battle_active:
        await update.message.reply_text("⚔️ Битва уже идёт!")
        return

    if len(players) < 2:
        await update.message.reply_text("❌ Нужно минимум 2 участника.")
        return

    battle_active = True

    await update.message.reply_text(
        "🔥 БИТВА НИКОВ НАЧАЛАСЬ!\n"
        f"Участники: {', '.join('@' + p for p in players)}"
    )

    await asyncio.sleep(2)

    winner = random.choice(list(players))

    await update.message.reply_text(
        f"🏆 ПОБЕДИТЕЛЬ:\n"
        f"🥇 @{winner}"
    )

    # Сброс
    players.clear()
    battle_active = False


# ====== ЗАПУСК ======

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("battle", battle))

    print("🤖 Battle Bot запущен")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
