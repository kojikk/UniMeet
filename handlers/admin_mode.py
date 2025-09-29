"""
Система админского режима - переключение между пользовательским и админским интерфейсом
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import Database
from config import DATABASE_URL
from utils import is_admin

router = Router()
db = Database(DATABASE_URL)

# Словарь для хранения режима пользователей (в реальном проекте лучше использовать Redis)
admin_modes = {}

def is_in_admin_mode(user_id: int) -> bool:
    """Проверить, находится ли пользователь в админском режиме"""
    return admin_modes.get(user_id, False)

def set_admin_mode(user_id: int, mode: bool):
    """Установить админский режим для пользователя"""
    if mode:
        admin_modes[user_id] = True
    else:
        admin_modes.pop(user_id, None)

@router.message(F.text == "🔧 Админ панель")
async def enter_admin_mode(message: Message):
    """Войти в админский режим"""
    if not is_admin(message):
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    set_admin_mode(message.from_user.id, True)
    
    from handlers.menu import get_main_menu_keyboard
    
    await message.answer(
        "🔧 **Добро пожаловать в админ-панель!**\n\n"
        "Теперь ты видишь админское меню.\n"
        "Для выхода используй кнопку **Выйти из админки**.",
        reply_markup=get_main_menu_keyboard(admin_mode=True)
    )

@router.message(F.text == "🚪 Выйти из админки")
async def exit_admin_mode(message: Message):
    """Выйти из админского режима"""
    if not is_admin(message):
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    set_admin_mode(message.from_user.id, False)
    
    # Получаем статус пользователя для правильного меню
    user = await db.get_user(message.from_user.id)
    user_status = user['verification_status'] if user else None
    is_user_admin = is_admin(message)
    
    from handlers.menu import get_main_menu_keyboard
    
    await message.answer(
        "🚪 **Выход из админ-панели**\n\n"
        "Теперь ты видишь обычное пользовательское меню.\n"
        "Для входа в админку используй кнопку **Админ панель**.",
        reply_markup=get_main_menu_keyboard(user_status, is_user_admin, admin_mode=False)
    )

@router.message(F.text == "📋 Заявки на верификацию")
async def admin_pending_menu(message: Message):
    """Заявки на верификацию через админское меню"""
    if not is_admin(message) or not is_in_admin_mode(message.from_user.id):
        await message.answer("❌ Доступно только в админском режиме.")
        return
    
    from handlers.admin import pending_command
    await pending_command(message)

@router.message(F.text == "🎉 Управление мероприятиями")
async def admin_events_menu(message: Message):
    """Управление мероприятиями через админское меню"""
    if not is_admin(message) or not is_in_admin_mode(message.from_user.id):
        await message.answer("❌ Доступно только в админском режиме.")
        return
    
    from handlers.events import admin_events_command
    await admin_events_command(message)

@router.message(F.text == "📊 Статистика")
async def admin_stats_menu(message: Message):
    """Статистика через админское меню"""
    if not is_admin(message) or not is_in_admin_mode(message.from_user.id):
        await message.answer("❌ Доступно только в админском режиме.")
        return
    
    # Получаем статистику
    users_count = await get_users_stats()
    events_count = await get_events_stats()
    pending_count = len(await db.get_pending_verifications())
    
    await message.answer(
        f"📊 **Статистика системы**\n\n"
        f"👥 **Пользователи:**\n"
        f"• Всего: {users_count['total']}\n"
        f"• Верифицировано: {users_count['approved']}\n"
        f"• На модерации: {users_count['pending']}\n"
        f"• Отклонено: {users_count['rejected']}\n\n"
        f"🎉 **Мероприятия:**\n"
        f"• Всего: {events_count['total']}\n"
        f"• Активных: {events_count['active']}\n\n"
        f"📋 **Заявки на рассмотрении:** {pending_count}"
    )

async def get_users_stats():
    """Получить статистику пользователей"""
    async with db._connect() as conn:
        cursor = await conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN verification_status = 'approved' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN verification_status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN verification_status = 'rejected' THEN 1 ELSE 0 END) as rejected
            FROM users 
            WHERE name IS NOT NULL
        """)
        row = await cursor.fetchone()
        return {
            'total': row[0] or 0,
            'approved': row[1] or 0,
            'pending': row[2] or 0,
            'rejected': row[3] or 0
        }

async def get_events_stats():
    """Получить статистику мероприятий"""
    async with db._connect() as conn:
        cursor = await conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_active = TRUE THEN 1 ELSE 0 END) as active
            FROM events
        """)
        row = await cursor.fetchone()
        return {
            'total': row[0] or 0,
            'active': row[1] or 0
        }

# Добавляем метод для подключения к базе в класс Database
def _connect(self):
    """Прямое подключение к базе данных (для статистики)"""
    import aiosqlite
    return aiosqlite.connect(self.db_path)

# Патчим класс Database
Database._connect = _connect
