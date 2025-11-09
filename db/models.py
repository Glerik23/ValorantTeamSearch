# Моделі бази даних
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
from config import MAX_RIOT_ID_LENGTH, MAX_RANK_LENGTH, MAX_ROLE_LENGTH, MAX_BIO_LENGTH, MAX_CONTACT_LENGTH, MAX_USERNAME_LENGTH, MAX_STATUS_LENGTH

Base = declarative_base()


class User(Base):
    """Модель користувача"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(MAX_USERNAME_LENGTH))
    is_moderator = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Application(Base):
    """Модель анкети"""
    __tablename__ = 'applications'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(String(MAX_STATUS_LENGTH), default='pending')  # pending, approved, rejected
    riot_id = Column(String(MAX_RIOT_ID_LENGTH), nullable=False)
    age = Column(Integer, nullable=False)
    rank = Column(String(MAX_RANK_LENGTH), nullable=False)
    role = Column(String(MAX_ROLE_LENGTH), nullable=False)
    agents = Column(Text, nullable=False)  # Зберігаємо як JSON строку
    server = Column(Text, nullable=False)  # Зберігаємо як JSON строку
    bio = Column(String(MAX_BIO_LENGTH))
    contact_info = Column(String(MAX_CONTACT_LENGTH), nullable=False)
    moderator_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    channel_message_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))