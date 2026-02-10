from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String)
    active = Column(Boolean, default=True)
    current_round = Column(Integer, default=1)
    invites = Column(Integer, default=0)

class Invite(Base):
    __tablename__ = "invites"

    id = Column(Integer, primary_key=True)
    inviter_id = Column(Integer, ForeignKey("users.id"))
    invited_id = Column(Integer, unique=True)

class Tournament(Base):
    __tablename__ = "tournament"

    id = Column(Integer, primary_key=True)
    round = Column(Integer, default=1)
    deadline = Column(DateTime, default=datetime.utcnow)
