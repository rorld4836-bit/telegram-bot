import os
import json
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================= НАСТРОЙКИ =================
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = "battlertf"
STATE_FILE = "state.json"
ROUND_TIME = 15 * 60
MIN_PARTICIPANTS = 2

# ================= СОСТОЯНИЕ =================
STATE = {
    "round": 0,
    "active": False,
    "participants": [],
    "posts": {},
    "votes": {},
    "user_data": {}
}

# ================= SAVE / LOAD =================
def save_state():
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(STATE, f, ensure_ascii=False, indent=2)

def load_state():
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            STATE.update(json.load(f))
    except:
        print("Ошибка загрузки state.json")

# ================= МЕНЮ =================
def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚔️ Участвовать", callback_data="join"),
            InlineKeyboardButton("📜 Правила", callback_data="rules")
        ],
        [
            InlineKeyboardButton("🔍 Найти себя", callback_data="find_me"),
            InlineKeyboardButton("🔗 Пригласить", callback_data="invite")
        ]
    ])

# ================= /START + РЕФЕРАЛЫ =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id

    if uid not in STATE["user_data"]:
        STATE["user_data"][uid] = {
            "votes": 0,
            "invites": 0,
            "wins": 0,
            "referrals": []
        }

    # обработка реферала
    if context.args:
        referrer_id = context.args[0]

        if referrer_id.isdigit():
            referrer_id = int(referrer_id)

            if referrer_id != uid:
                if referrer_id in STATE["user_data"]:
                    if uid not in STATE["user_data"][referrer_id]["referrals"]:
                        STATE["user_data"][referrer_id]["invites"] += 1
                        STATE["user_data"][referrer_id]["referrals"].append(uid)
                        save_state()

    save_state()

    await update.message.reply_text(
        "🔥 *Добро пожаловать в Битву Ников!*\n\n"
        f"Турнир проходит в канале:\n👉 https://t.me/{CHANNEL}\n\n"
        "Используй кнопки ниже 👇",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ================= ПРАВИЛА =================
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "📜 *ПРАВИЛА БИТВЫ НИКОВ*\n\n"
        "⚔️ Формат турнира\n"
        "• Раунды запускаются автоматически\n"
        "• Участники могут присоединяться во время раунда\n\n"
        "🗳 Голосование\n"
        "• 1 пользователь = 1 голос\n"
        "• Повторное голосование запрещено\n\n"
        "🏆 Победа\n"
        "• После каждого раунда часть игроков выбывает\n"
        "• В финале остаётся 1 победитель\n\n"
        "🔐 Бот не передаёт личные данные",
        parse_mode="Markdown"
    )

# ================= УЧАСТВОВАТЬ =================
async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id

    if uid in STATE["participants"]:
        await q.answer("Ты уже участвуешь!", show_alert=True)
        return

    STATE["participants"].append(uid)

    if uid not in STATE["user_data"]:
        STATE["user_data"][uid] = {
            "votes": 0,
            "invites": 0,
            "wins": 0,
            "referrals": []
        }

    save_state()
    await q.answer("Ты в турнире!")

# ================= НАЙТИ СЕБЯ =================
async def find_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = str(q.from_user.id)

    msg_id = STATE["posts"].get(uid)

    if not msg_id:
        await q.answer("Ты сейчас не участвуешь", show_alert=True)
        return

    await q.message.reply_text(
        "🔍 Твоя битва:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "➡️ Перейти к битве",
                url=f"https://t.me/{CHANNEL}/{msg_id}"
            )
        ]])
    )

    await q.answer()

# ================= ПРИГЛАСИТЬ =================
async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id

    link = f"https://t.me/{context.bot.username}?start={uid}"

    await q.answer()
    await q.message.reply_text(
        f"🔗 Твоя реферальная ссылка:\n{link}"
    )

# ================= ROUTER =================
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data

    if data == "join":
        await join(update, context)

    elif data == "rules":
        await rules(update, context)

    elif data == "find_me":
        await find_me(update, context)

    elif data == "invite":
        await invite(update, context)

# ================= MAIN =================
def main():
    load_state()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(router))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
