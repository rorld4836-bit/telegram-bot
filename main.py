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

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = "battlertf"
STATE_FILE = "state.json"

ROUND_TIME = 60 * 15  # 15 минут

# ===== СОСТОЯНИЕ =====
STATE = {
    "round": 0,
    "active": False,
    "participants": [],
    "posts": {},
    "votes": {}
}

# ===== SAVE / LOAD =====
def save_state():
    data = {
        "round": STATE["round"],
        "active": STATE["active"],
        "participants": STATE["participants"],
        "posts": STATE["posts"],
        "votes": {k: list(v) for k, v in STATE["votes"].items()}
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_state():
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            STATE["round"] = data.get("round", 0)
            STATE["active"] = data.get("active", False)
            STATE["participants"] = data.get("participants", [])
            STATE["posts"] = data.get("posts", {})
            STATE["votes"] = defaultdict(set, {
                int(k): set(v) for k, v in data.get("votes", {}).items()
            })
    except Exception:
        print("⚠️ Не удалось загрузить state.json")

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚔️ Участвовать", callback_data="join"),
            InlineKeyboardButton("📜 Правила", callback_data="rules")
        ],
        [
            InlineKeyboardButton("🔍 Найти себя", callback_data="find_me")
        ]
    ])
    await update.message.reply_text(
        "🔥 Битва Ников\n\nНажми кнопку ниже 👇",
        reply_markup=kb
    )

# ===== RULES =====
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "📜 ПРАВИЛА\n\n"
        "• Участники могут добавляться в любой момент\n"
        "• Раунды автоматические\n"
        "• 1 пользователь = 1 голос\n"
        "• Проигравшие ждут следующий турнир\n"
        "• 4–5 раунд — редкость\n"
        "• В финале только 1 победитель\n\n"
        "🔐 Конфиденциальность игроков полностью защищена."
    )

# ===== JOIN =====
async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id

    if uid in STATE["participants"]:
        await q.answer("Ты уже участвуешь", show_alert=True)
        return

    STATE["participants"].append(uid)
    save_state()

    await q.answer("Ты в битве!")

    if not STATE["active"]:
        asyncio.create_task(start_round(context))

# ===== START ROUND =====
async def start_round(context):
    if len(STATE["participants"]) < 2:
        return

    STATE["active"] = True
    STATE["round"] += 1
    STATE["votes"] = defaultdict(set)
    STATE["posts"].clear()
    save_state()

    await context.bot.send_message(
        chat_id=f"@{CHANNEL}",
        text=f"⚔️ Раунд {STATE['round']} начинается!"
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
        STATE["posts"][uid] = msg.message_id

    save_state()
    await asyncio.sleep(ROUND_TIME)
    await end_round(context)

# ===== END ROUND =====
async def end_round(context):
    scores = []
    for uid, msg_id in STATE["posts"].items():
        scores.append((uid, len(STATE["votes"].get(msg_id, []))))

    scores.sort(key=lambda x: x[1], reverse=True)
    winners = scores[:max(1, len(scores)//2)]

    STATE["participants"] = [uid for uid, _ in winners]
    STATE["posts"].clear()
    save_state()

    await context.bot.send_message(
        chat_id=f"@{CHANNEL}",
        text=f"✅ Раунд {STATE['round']} завершён"
    )

    if len(STATE["participants"]) == 1:
        user = await context.bot.get_chat(STATE["participants"][0])
        await context.bot.send_message(
            chat_id=f"@{CHANNEL}",
            text=f"🏆 ПОБЕДИТЕЛЬ\n@{user.username or user.first_name}"
        )
        STATE["active"] = False
        STATE["participants"].clear()
        save_state()
        return

    asyncio.create_task(start_round(context))

# ===== VOTE =====
async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    msg_id = q.message.message_id

    if uid in STATE["votes"].get(msg_id, set()):
        await q.answer("Ты уже голосовал", show_alert=True)
        return

    STATE["votes"].setdefault(msg_id, set()).add(uid)
    save_state()
    await q.answer("Голос засчитан 👍")

# ===== FIND ME =====
async def find_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id

    msg_id = STATE["posts"].get(uid)
    if not msg_id:
        await q.answer("Ты сейчас не в раунде", show_alert=True)
        return

    await q.message.reply_text(
        "🔍 Твоя битва:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "➡️ Перейти",
                url=f"https://t.me/{CHANNEL}/{msg_id}"
            )
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
