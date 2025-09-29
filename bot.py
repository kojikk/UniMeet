import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, DATABASE_URL, DEBUG, ADMIN_IDS
from database import Database
from handlers.registration import router as registration_router
from handlers.admin import router as admin_router
from handlers.menu import router as menu_router
from handlers.events import router as events_router
# admin_mode_router объединен с admin_router

# Настройка логирования
log_level = logging.DEBUG if DEBUG else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция запуска бота"""
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Инициализация базы данных
    db = Database(DATABASE_URL)
    await db.init_db()
    
    # Инициализация админов из конфига
    for admin_id in ADMIN_IDS:
        await db.add_admin(admin_id, is_super_admin=True)
    
    # Регистрация роутеров
    dp.include_router(admin_router)  # Админские функции (включая режим переключения)
    dp.include_router(menu_router)  # Меню
    dp.include_router(events_router)  # Мероприятия
    dp.include_router(registration_router)
    
    logger.info("Бот запускается...")
    
    try:
        # Запуск бота
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
