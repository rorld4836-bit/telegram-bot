import os
import json
import random
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================= НАСТРОЙКИ =================

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "battlertf"   # без @
ROUND_DURATION = 7 * 60 * 60     # 7 часов
MIN_PLAYERS = 2
MAX_PLAYERS = 16
STATE_FILE = "state.json"

# ================= СОСТОЯНИЕ =================

STATE = {
    "participants": [],
    "active_round": False,
    "round_number": 0,
    "battles": [],          # список боёв текущего раунда
    "votes": {},            # battle_id -> {user_id: vote}
    "battle_messages": {},  # battle_id -> message_id
    "round_end_time": None
}

# ================= SAVE / LOAD =================

def save_state():
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(STATE, f)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            STATE.update(json.load(f))

# ================= МЕНЮ =================

def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚔️ Участвовать", callback_data="join"),
            InlineKeyboardButton("🔍 Найти себя", callback_data="find_me")
        ],
        [
            InlineKeyboardButton("📜 Правила", callback_data="rules"),
            InlineKeyboardButton("🔗 Пригласить", callback_data="invite")
        ]
    ])

# ================= /START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Добро пожаловать в Битву Ников!\n\n"
        f"Турнир проходит здесь:\n👉 https://t.me/{CHANNEL_USERNAME}",
        reply_markup=main_menu()
    )

# ================= JOIN =================

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id

    if user_id in STATE["participants"]:
        await q.message.reply_text("Ты уже участвуешь.")
        return

    STATE["participants"].append(user_id)
    save_state()

    await q.message.reply_text("✅ Ты добавлен в турнир!")

# ================= FIND ME =================

async def find_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id

    for battle_id, battle in enumerate(STATE["battles"]):
        if user_id in battle:
            msg_id = STATE["battle_messages"].get(str(battle_id))
            if msg_id:
                link = f"https://t.me/{CHANNEL_USERNAME}/{msg_id}"
                await q.message.reply_text(
                    "Твоя битва:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Перейти", url=link)]
                    ])
                )
                return

    await q.message.reply_text("Ты сейчас не в активной битве.")

# ================= ПРАВИЛА =================

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    await q.message.reply_text(
        "📜 ПРАВИЛА БИТВЫ НИКОВ\n\n"
        "• Раунд длится 7 часов\n"
        "• 1 пользователь = 1 голос\n"
        "• Нельзя голосовать дважды\n"
        "• В финале всегда 1 победитель\n"
        "• Конфиденциальность игроков защищена"
    )

# ================= INVITE =================

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    link = f"https://t.me/{context.bot.username}?start={q.from_user.id}"
    await q.message.reply_text(f"Твоя реферальная ссылка:\n{link}")

# ================= СТАРТ РАУНДА =================

async def start_round(context: ContextTypes.DEFAULT_TYPE):

    if len(STATE["participants"]) < MIN_PLAYERS:
        return

    STATE["active_round"] = True
    STATE["round_number"] += 1
    STATE["battles"] = []
    STATE["votes"] = {}
    STATE["battle_messages"] = {}

    players = STATE["participants"][:]
    random.shuffle(players)

    for i in range(0, len(players), 2):
        if i + 1 < len(players):
            STATE["battles"].append([players[i], players[i+1]])

    for battle_id, battle in enumerate(STATE["battles"]):

        text = (
            f"🔥 Битвы Ников\n"
            f"Раунд {STATE['round_number']}\n\n"
            f"⚔️ Два отважных воина сходятся в битве!\n\n"
            f"<a href='tg://user?id={battle[0]}'>Игрок 1</a> "
            f"VS "
            f"<a href='tg://user?id={battle[1]}'>Игрок 2</a>\n\n"
            f"⏳ Время: 7 часов"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👍 Голос 1", callback_data=f"vote_{battle_id}_0"),
                InlineKeyboardButton("👍 Голос 2", callback_data=f"vote_{battle_id}_1")
            ]
        ])

        msg = await context.bot.send_message(
            chat_id=f"@{CHANNEL_USERNAME}",
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        STATE["battle_messages"][str(battle_id)] = msg.message_id
        STATE["votes"][str(battle_id)] = {}

    STATE["round_end_time"] = (datetime.utcnow() + timedelta(seconds=ROUND_DURATION)).isoformat()

    save_state()

    context.job_queue.run_once(end_round, ROUND_DURATION)

# ================= ГОЛОСОВАНИЕ =================

async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data.split("_")
    battle_id = data[1]
    choice = data[2]
    user_id = q.from_user.id

    if user_id in STATE["votes"][battle_id]:
        await q.answer("Ты уже голосовал!", show_alert=True)
        return

    battle = STATE["battles"][int(battle_id)]

    if battle[int(choice)] == user_id:
        await q.answer("Нельзя голосовать за себя!", show_alert=True)
        return

    STATE["votes"][battle_id][user_id] = int(choice)
    save_state()

# ================= ЗАВЕРШЕНИЕ РАУНДА =================

async def end_round(context: ContextTypes.DEFAULT_TYPE):

    winners = []

    for battle_id, battle in enumerate(STATE["battles"]):
        votes = STATE["votes"].get(str(battle_id), {})

        count0 = sum(1 for v in votes.values() if v == 0)
        count1 = sum(1 for v in votes.values() if v == 1)

        winner = battle[0] if count0 >= count1 else battle[1]
        winners.append(winner)

    STATE["participants"] = winners
    STATE["active_round"] = False

    if len(winners) == 1:
        await context.bot.send_message(
            chat_id=f"@{CHANNEL_USERNAME}",
            text=f"🏆 Победитель турнира!\n\n<a href='tg://user?id={winners[0]}'>Чемпион</a>",
            parse_mode="HTML"
        )
        STATE["round_number"] = 0
        STATE["participants"] = []
    else:
        await start_round(context)

    save_state()

# ================= ROUTER =================

async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data

    if data == "join":
        await join(update, context)
    elif data == "find_me":
        await find_me(update, context)
    elif data == "rules":
        await rules(update, context)
    elif data == "invite":
        await invite(update, context)
    elif data.startswith("vote_"):
        await vote(update, context)

# ================= MAIN =================

def main():
    load_state()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(router))

    app.job_queue.run_repeating(
        lambda ctx: start_round(ctx) if not STATE["active_round"] else None,
        interval=60,
        first=10
    )

    print("Турнирный движок запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
