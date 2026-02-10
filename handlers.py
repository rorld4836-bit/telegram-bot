from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from database import SessionLocal
from models import User, Invite

def keyboard():
    return ReplyKeyboardMarkup(
        [["🚀 Участвовать"], ["📊 Прогресс", "📜 Правила"]],
        resize_keyboard=True
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = SessionLocal()
    user = update.effective_user
    args = context.args

    db_user = session.get(User, user.id)
    if not db_user:
        db_user = User(id=user.id, username=user.username)
        session.add(db_user)
        session.commit()

    if args and args[0].startswith("ref_"):
        inviter_id = int(args[0].split("_")[1])
        if inviter_id != user.id:
            exists = session.query(Invite).filter_by(invited_id=user.id).first()
            if not exists:
                session.add(Invite(inviter_id=inviter_id, invited_id=user.id))
                inviter = session.get(User, inviter_id)
                if inviter:
                    inviter.invites += 1
                session.commit()

    await update.message.reply_text(
        "Добро пожаловать в турнир ⚔️",
        reply_markup=keyboard()
    )
    session.close()
