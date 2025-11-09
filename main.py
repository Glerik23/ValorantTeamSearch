# Головний файл бота
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from db.requests import create_tables
from handlers import user_handlers, admin_handlers


# Налаштування логування
def setup_logging():
    """Налаштування логування для всіх модулів"""
    LOG_DIR = Path("logs")
    LOG_DIR.mkdir(exist_ok=True)

    # Формат логів
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler для файлу (ротація при досягненні 5MB, зберігає 3 файли)
    file_handler = RotatingFileHandler(
        LOG_DIR / "bot.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Handler для консолі
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Налаштовуємо кореневий логер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Видаляємо існуючі handlers, щоб уникнути дублювання
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Додаємо наші handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Налаштування логування для aiogram (менше спаму)
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


async def main():
    """Головна функція запуску бота"""
    # Налаштовуємо логування перед запуском
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 50)
    logger.info("Запуск бота...")

    # Створюємо бота та диспетчер
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Створюємо таблиці в базі даних
    await create_tables()
    logger.info("Таблиці бази даних перевірено/створено")

    # Реєструємо роутери
    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)
    logger.info("Роутери зареєстровано")

    # Запускаємо бота
    logger.info("Бот запущено та готовий до роботи!")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Критична помилка: {e}", exc_info=True)
    finally:
        await bot.session.close()
        logger.info("Бот зупинено")


if __name__ == "__main__":
    asyncio.run(main())