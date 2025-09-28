from typing import Union
from aiogram.types import Message, CallbackQuery
from config import ADMIN_IDS, ADMIN_USERNAMES

def is_admin(user: Union[Message, CallbackQuery]) -> bool:
    """Проверка, является ли пользователь администратором"""
    # Получаем объект пользователя в зависимости от типа
    if isinstance(user, Message):
        telegram_user = user.from_user
    elif isinstance(user, CallbackQuery):
        telegram_user = user.from_user
    else:
        return False
    
    if not telegram_user:
        return False
    
    # Проверяем по ID
    if telegram_user.id in ADMIN_IDS:
        return True
    
    # Проверяем по username
    if telegram_user.username and telegram_user.username.lower() in ADMIN_USERNAMES:
        return True
    
    return False

def get_user_display_name(telegram_user) -> str:
    """Получить отображаемое имя пользователя"""
    if telegram_user.username:
        return f"@{telegram_user.username}"
    elif telegram_user.first_name:
        name = telegram_user.first_name
        if telegram_user.last_name:
            name += f" {telegram_user.last_name}"
        return name
    else:
        return f"User {telegram_user.id}"
