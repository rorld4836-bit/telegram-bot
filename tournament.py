from datetime import datetime, timedelta
from database import SessionLocal
from models import Tournament
from config import ROUND_DURATION_HOURS

def get_tournament():
    session = SessionLocal()
    t = session.query(Tournament).first()
    if not t:
        t = Tournament(
            round=1,
            deadline=datetime.utcnow() + timedelta(hours=ROUND_DURATION_HOURS)
        )
        session.add(t)
        session.commit()
    session.close()
    return t
