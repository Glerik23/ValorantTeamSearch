# Функції для роботи з базою даних
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import json
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging
from db.models import User, Application, Base
from config import DATABASE_URL

# Налаштування логування для цього модуля
logger = logging.getLogger(__name__)

# Створюємо асинхронний рушій БД
engine = create_async_engine(DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://"), echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables():
    """Створення таблиць в базі даних"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def add_user(telegram_id: int, username: str = None) -> User:
    """Додавання нового користувача"""
    async with AsyncSessionLocal() as session:
        # Перевіряємо чи існує користувач
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()

        if not user:
            user = User(telegram_id=telegram_id, username=username)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user


async def create_application(user_id: int, riot_id: str, age: int, rank: str,
                             role: str, agents: list, server: list, bio: str, contact_info: str) -> Optional[Application]:
    """Створення нової анкети"""
    async with AsyncSessionLocal() as session:
        # Перевіряємо наявність активних анкет (pending або approved)
        result = await session.execute(
            select(Application).where(
                (Application.user_id == user_id) &
                (Application.status.in_(['pending', 'approved']))
            )
        )
        active_application = result.scalar_one_or_none()

        if active_application:
            return None  # Повертаємо None якщо вже є активна анкета

        application = Application(
            user_id=user_id,
            riot_id=riot_id,
            age=age,
            rank=rank,
            role=role,
            agents=json.dumps(agents),
            server=json.dumps(server),
            bio=bio,
            contact_info=contact_info,
            status='pending'
        )

        session.add(application)
        await session.commit()
        await session.refresh(application)
        return application


async def get_user_applications(telegram_id: int) -> list:
    """Отримання анкет користувача по telegram_id"""
    async with AsyncSessionLocal() as session:
        # Спочатку знаходимо user_id по telegram_id
        user_result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = user_result.scalar_one_or_none()

        if not user:
            return []

        result = await session.execute(
            select(Application).where(Application.user_id == user.id).order_by(Application.created_at.desc())
        )
        applications = result.scalars().all()

        # Приводимо всі дати к UTC для консистентности
        for app in applications:
            if app.created_at.tzinfo is None:
                app.created_at = app.created_at.replace(tzinfo=timezone.utc)

        return applications


async def get_pending_applications() -> list:
    """Отримання анкет що очікують модерації"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Application).where(Application.status == 'pending').order_by(Application.created_at)
        )
        applications = result.scalars().all()

        # Приводимо всі дати к UTC для консистентности
        for app in applications:
            if app.created_at.tzinfo is None:
                app.created_at = app.created_at.replace(tzinfo=timezone.utc)

        return applications


async def update_application_status(application_id: int, status: str, moderator_id: int = None) -> bool:
    """Оновлення статусу анкети"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Application).where(Application.id == application_id))
        application = result.scalar_one_or_none()

        if application:
            application.status = status
            application.moderator_id = moderator_id
            application.updated_at = datetime.now(timezone.utc)
            await session.commit()
            return True
        return False

async def update_application_channel_message(application_id: int, channel_message_id: int) -> bool:
    """Оновлення ID повідомлення в каналі"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Application).where(Application.id == application_id))
        application = result.scalar_one_or_none()

        if application:
            application.channel_message_id = channel_message_id
            await session.commit()
            return True
        return False

async def delete_application(application_id: int) -> bool:
    """Повне видалення анкети з бази даних"""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(Application).where(Application.id == application_id))
            application = result.scalar_one_or_none()

            if application:
                await session.delete(application)
                await session.commit()
                logger.info(f"Анкета #{application_id} повністю видалена з бази даних")
                return True
            else:
                logger.warning(f"Спроба видалити неіснуючу анкету #{application_id}")
                return False
        except Exception as e:
            logger.error(f"Помилка при видаленні анкети #{application_id}: {e}")
            await session.rollback()
            return False


async def get_application_by_id(application_id: int) -> Application:
    """Отримання анкети по ID"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Application).where(Application.id == application_id))
        application = result.scalar_one_or_none()

        if application and application.created_at.tzinfo is None:
            application.created_at = application.created_at.replace(tzinfo=timezone.utc)

        return application


async def get_user_by_id(user_id: int) -> User:
    """Отримання користувача по ID"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


async def get_user_by_telegram_id(telegram_id: int) -> User:
    """Отримання користувача по Telegram ID"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()


async def get_user_by_username(username: str) -> User:
    """Отримання користувача по username"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()


async def set_moderator_status(user_id: int, is_moderator: bool) -> bool:
    """Встановлення статусу модератора"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user:
            user.is_moderator = is_moderator
            await session.commit()
            return True
        return False


async def get_all_moderators() -> list:
    """Отримання всіх модераторів"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.is_moderator == True))
        return result.scalars().all()