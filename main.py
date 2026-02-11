import os
import json
import asyncio
from collections import defaultdict
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

# ===== НАСТРОЙКИ =====
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = "battlertf"
STATE_FILE = "state.json"
ROUND_TIME = 15 * 60  # 15 минут
MIN_PARTICIPANTS = 2  # Минимальное количество участников для старта

# ===== СОСТОЯНИЕ =====
STATE = {
    "round": 0,
    "active": False,
    "participants": [],
    "posts": {},      # user_id -> message_id
    "votes": {},      # message_id -> [user_id]
    "user_data": {}   # user_id -> { 'votes': 0, 'invites': 0, 'wins': 0 }
}

# ===== SAVE / LOAD =====
def save_state():
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(STATE, f, ensure_ascii=False, indent=2)

def load_state():
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            STATE.update(data)
    except Exception:
        print("⚠️ Ошибка загрузки state.json")

# ===== INLINE МЕНЮ =====
def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚔️ Участвовать", callback_data="join"),
            InlineKeyboardButton("📜 Правила", callback_data="rules")
        ],
        [
            InlineKeyboardButton("🔍 Найти себя", callback_data="find_me")
        ]
    ])

# ===== /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 *Добро пожаловать в Битву Ников!*\n\n"
        "Турнир проходит в канале:\n"
        f"👉 https://t.me/{CHANNEL}\n\n"
        "Используй кнопки ниже 👇",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ===== ПРАВИЛА =====
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "📜 *ПРАВИЛА БИТВЫ НИКОВ*\n\n"
        "⚔️ *Формат турнира*\n"
        "• Участники могут присоединяться даже во время раунда\n"
        "• Раунды запускаются автоматически\n"
        "• Один раунд = ограниченное время\n\n"
        "🗳 *Голосование*\n"
        "• 1 пользователь = 1 голос за участника\n"
        "• Повторное голосование запрещено\n"
        "• Накрутка не поощряется\n\n"
        "🏆 *Победа*\n"
        "• После каждого раунда часть игроков выбывает\n"
        "• 4–5 раунд — редкость\n"
        "• В финале ВСЕГДА только 1 победитель\n\n"
        "⛔ *Важно*\n"
        "• Проигравшие ждут следующий турнир\n"
        "• Награды выдаются вручную администратором\n\n"
        "🔐 *Конфиденциальность*\n"
        "• Бот не передаёт личные данные\n"
        "• Используются только ID и никнеймы\n"
        "• Все данные защищены",
        parse_mode="Markdown"
    )

# ===== УЧАСТИЕ =====
async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id

    if uid in STATE["participants"]:
        await q.answer("Ты уже участвуешь!", show_alert=True)
        return

    STATE["participants"].append(uid)
    STATE["user_data"][uid] = {'votes': 0, 'invites': 0, 'wins': 0}  # инициализация статистики
    save_state()
    await q.answer("Ты в битве!")

    if not STATE["active"] and len(STATE["participants"]) >= MIN_PARTICIPANTS:
        asyncio.create_task(start_round(context))

# ===== СТАРТ РАУНДА =====
async def start_round(context):
    if len(STATE["participants"]) < MIN_PARTICIPANTS:
        await context.bot.send_message(
            chat_id=f"@{CHANNEL}",
            text=f"⚔️ *Недостаточно участников для начала турнира.* Пожалуйста, пригласите ещё людей!",
            parse_mode="Markdown"
        )
        return

    STATE["active"] = True
    STATE["round"] += 1
    STATE["votes"] = {}
    STATE["posts"].clear()
    save_state()

    await context.bot.send_message(
        chat_id=f"@{CHANNEL}",
        text=f"⚔️ *Раунд {STATE['round']} начался!*",
        parse_mode="Markdown"
    )

    for uid in STATE["participants"]:
        user = await context.bot.get_chat(uid)
        msg = await context.bot.send_message(
            chat_id=f"@{CHANNEL}",
            text=f"⚔️ Раунд {STATE['round']}\n@{user.username or user.first_name}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("👍 Проголосовать", callback_data=f"vote:{uid}")
            ]])
        )
        STATE["posts"][str(uid)] = msg.message_id
        STATE["votes"][str(msg.message_id)] = []

    save_state()
    await asyncio.sleep(ROUND_TIME)
    await end_round(context)

# ===== КОНЕЦ РАУНДА =====
async def end_round(context):
    scores = []

    for uid, msg_id in STATE["posts"].items():
        votes = len(STATE["votes"].get(str(msg_id), []))
        scores.append((int(uid), votes))

    scores.sort(key=lambda x: x[1], reverse=True)
    winners = scores[:max(1, len(scores)//2)]
    STATE["participants"] = [uid for uid, _ in winners]
    save_state()

    await context.bot.send_message(
        chat_id=f"@{CHANNEL}",
        text=f"✅ Раунд {STATE['round']} завершён"
    )

    if len(STATE["participants"]) == 1:
        user = await context.bot.get_chat(STATE["participants"][0])
        STATE["user_data"][STATE["participants"][0]]['wins'] += 1
        save_state()
        await context.bot.send_message(
            chat_id=f"@{CHANNEL}",
            text=f"🏆 *ПОБЕДИТЕЛЬ ТУРНИРА*\n@{user.username or user.first_name}",
            parse_mode="Markdown"
        )
        STATE["active"] = False
        STATE["participants"].clear()
        save_state()
        return

    asyncio.create_task(start_round(context))

# ===== ГОЛОС =====
async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    voter = q.from_user.id
    msg_id = str(q.message.message_id)

    if voter in STATE["votes"].get(msg_id, []):
        await q.answer("Ты уже голосовал", show_alert=True)
        return

    STATE["votes"].setdefault(msg_id, []).append(voter)
    STATE["user_data"][voter]['votes'] += 1  # Увеличиваем количество голосов
    save_state()
    await q.answer("Голос принят 👍")

# ===== НАЙТИ СЕБЯ =====
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
            InlineKeyboardButton("➡️ Перейти к битве", url=f"https://t.me/{CHANNEL}/{msg_id}")
        ]])
    )
    await q.answer()

# ===== ROUTER =====
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if data == "join":
        await join(update, context)
    elif data == "rules":
        await rules(update, context)
    elif data == "find_me":
        await find_me(update, context)
    elif data.startswith("vote"):
        await vote(update, context)

# ===== MAIN =====
def main():
    load_state()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(router))
    app.run_polling()

if __name__ == "__main__":
    main()
