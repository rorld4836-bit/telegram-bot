import os

TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

BOT_LINK = "https://t.me/your_bot"
CHANNEL_LINK = "https://t.me/your_channel"

ROUND_DURATION_HOURS = 14

ROUNDS = {
    1: 5,
    2: 10,
    3: 15,
    4: 25
}

TIEBREAK_INVITES = 27
