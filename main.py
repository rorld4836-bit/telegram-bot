import os
import random
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# 🔐 ТОКЕН ИЗ RAILWAY VARIABLES
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден. Добавь его в Railway Variables.")


# ====== ДАННЫЕ В ПАМЯТИ ======
players = set()
battle_active = False


# ====== КОМАНДЫ ======

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет!\n"
        "⚔️ Бритва Ников — битва участников\n\n"
        "Команды:\n"
        "/join — участвовать\n"
        "/battle — начать битву\n"
        "/help — помощь"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 Команды бота:\n"
        "/start — запуск\n"
        "/join — участие\n"
        "/battle — битва\n"
        "/ping — проверка\n"
        "/about — о проекте"
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong! Бот онлайн.")


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Бритва Ников\n"
        "⚔️ Турнирный бот\n"
        "🚀 Работает на Railway"
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global battle_active

    if battle_active:
        await update.message.reply_text("⏳ Битва уже идёт. Жди следующий раунд.")
        return

    user = update.effective_user.username
    if not user:
        await update.message.reply_text("❌ Нужен username в Telegram.")
        return

    if user in players:
        await update.message.reply_text("ℹ️ Ты уже участвуешь.")
        return

    players.add(user)
    await update.message.reply_text(
        f"✅ @{user} участвует!\n"
        f"👥 Всего: {len(players)}"
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

    # 🔄 СБРОС
    players.clear()
    battle_active = False


# ====== ЗАПУСК ======

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("battle", battle))

    print("🤖 Бритва Ников запущена")
    app.run_polling()


if __name__ == "__main__":
    main()
