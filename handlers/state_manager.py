"""
Централизованный менеджер состояний пользователя.
Обеспечивает взаимоисключающие состояния - пользователь может быть только в одном состоянии.
"""

from aiogram.fsm.context import FSMContext
from aiogram import Bot
from aiogram.fsm.storage.base import StorageKey


async def clear_all_user_states(user_id: int, bot: Bot = None):
    """
    Очистить ВСЕ состояния пользователя:
    - FSM состояния (редактирование, создание и т.д.)
    - Админский режим
    """
    
    # 1. Очищаем FSM состояния
    if bot is not None:
        try:
            # Получаем dispatcher из бота
            dispatcher = getattr(bot, 'dispatcher', None)
            if dispatcher and hasattr(dispatcher, 'storage'):
                storage = dispatcher.storage
                key = StorageKey(bot.id, user_id, user_id)
                
                # Очищаем FSM состояние и данные
                await storage.set_state(key, None)
                await storage.set_data(key, {})
        except Exception:
            # Если не удалось очистить FSM - не критично
            pass
    
    # 2. Очищаем админский режим
    from handlers.admin import set_admin_mode
    set_admin_mode(user_id, False)


async def enter_admin_mode(user_id: int, bot: Bot = None):
    """
    Войти в админский режим с очисткой всех других состояний
    """
    # Сначала очищаем все состояния
    await clear_all_user_states(user_id, bot)
    
    # Затем включаем админский режим
    from handlers.admin import set_admin_mode
    set_admin_mode(user_id, True)


async def exit_admin_mode(user_id: int, bot: Bot = None):
    """
    Выйти из админского режима с очисткой состояний
    """
    # Очищаем все состояния (включая админский)
    await clear_all_user_states(user_id, bot)


async def start_user_operation(user_id: int, bot: Bot = None):
    """
    Начать пользовательскую операцию (редактирование, создание и т.д.)
    Выходим из админского режима если нужно
    """
    # Если пользователь в админском режиме - выходим из него
    from handlers.admin import is_in_admin_mode
    if is_in_admin_mode(user_id):
        await exit_admin_mode(user_id, bot)
    
    # Очищаем предыдущие FSM состояния
    if bot is not None:        
        try:
            dispatcher = getattr(bot, 'dispatcher', None) 
            if dispatcher and hasattr(dispatcher, 'storage'):
                storage = dispatcher.storage
                key = StorageKey(bot.id, user_id, user_id)
                
                # Очищаем только FSM, админский режим уже очищен выше
                await storage.set_state(key, None)
                await storage.set_data(key, {})
        except Exception:
            pass


def get_user_current_mode(user_id: int) -> str:
    """
    Получить текущий режим пользователя
    """
    from handlers.admin import is_in_admin_mode
    
    if is_in_admin_mode(user_id):
        return 'admin'
    else:
        return 'user'


def is_user_busy(user_id: int, current_fsm_state = None) -> bool:
    """
    Проверить, занят ли пользователь другими операциями
    """
    from handlers.admin import is_in_admin_mode
    
    # Если в админском режиме - занят
    if is_in_admin_mode(user_id):
        return True
    
    # Если есть активное FSM состояние - занят
    if current_fsm_state is not None:
        return True
    
    return False
