import random
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# 🔑 ТОКЕН
TOKEN = "ТВОЙ_ТОКЕН_ОТ_BOTFATHER"

# ====== ДАННЫЕ В ПАМЯТИ ======
players = set()
battle_active = False


# ====== КОМАНДЫ ======

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет!\n"
        "Это 🤖 Battle Bot — битва ников ⚔️\n\n"
        "Команды:\n"
        "/join — участвовать\n"
        "/battle — начать битву\n"
        "/help — помощь"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 Доступные команды:\n"
        "/start — запуск\n"
        "/join — участвовать\n"
        "/battle — начать битву\n"
        "/ping — проверить бота\n"
        "/about — о боте"
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong! Бот работает.")


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Battle Bot\n"
        "Версия 1.0\n"
        "Работает на Railway 🚀"
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global battle_active

    if battle_active:
        await update.message.reply_text("⚠️ Битва уже идёт. Жди следующую.")
        return

    user = update.effective_user.username
    if not user:
        await update.message.reply_text("❌ У тебя нет username в Telegram.")
        return

    players.add(user)
    await update.message.reply_text(
        f"✅ @{user} присоединился!\n"
        f"👥 Участников: {len(players)}"
    )


async def battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global battle_active, players

    if battle_active:
        await update.message.reply_text("⚔️ Битва уже идёт!")
        return

    if len(players) < 2:
        await update.message.reply_text("❌ Нужно минимум 2 участника.")
        return

    battle_active = True

    await update.message.reply_text(
        "🔥 БИТВА НИКОВ НАЧАЛАСЬ!\n\n"
        "Участники:\n" +
        "\n".join(f"@{p}" for p in players)
    )

    winner = random.choice(list(players))

    await update.message.reply_text(
        f"🏆 ПОБЕДИТЕЛЬ:\n"
        f"🥇 @{winner}"
    )

    # сброс
    players.clear()
    battle_active = False


# ====== ЗАПУСК БОТА ======

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("battle", battle))

    print("🤖 Battle Bot запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
