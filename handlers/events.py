from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
import logging

from database import Database
from config import DATABASE_URL
from utils import is_admin
from handlers.states import EventStates

router = Router()
db = Database(DATABASE_URL)
logger = logging.getLogger(__name__)

def get_events_list_keyboard(events, user_id=None):
    """Клавиатура со списком мероприятий"""
    keyboard = []
    
    if not events:
        keyboard.append([InlineKeyboardButton(text="📭 Мероприятий пока нет", callback_data="no_events")])
    else:
        for event in events:
            # Ограничиваем длину названия для красоты
            name = event['name'][:35] + "..." if len(event['name']) > 35 else event['name']
            keyboard.append([InlineKeyboardButton(
                text=f"🎉 {name}",
                callback_data=f"event_view_{event['id']}"
            )])
    
    keyboard.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="events_refresh")])
    keyboard.append([InlineKeyboardButton(text="🏠 Главная", callback_data="events_close")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_event_actions_keyboard(event_id, is_joined=False):
    """Клавиатура для действий с мероприятием"""
    keyboard = []
    
    if is_joined:
        keyboard.append([InlineKeyboardButton(
            text="❌ Отписаться", 
            callback_data=f"event_leave_{event_id}"
        )])
    else:
        keyboard.append([InlineKeyboardButton(
            text="✅ Записаться", 
            callback_data=f"event_join_{event_id}"
        )])
    
    keyboard.append([
        InlineKeyboardButton(text="⬅️ К списку", callback_data="events_list"),
        InlineKeyboardButton(text="🏠 Главная", callback_data="events_close")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_events_keyboard(events):
    """Админская клавиатура для управления мероприятиями"""
    keyboard = []
    
    # Кнопка создания нового мероприятия
    keyboard.append([InlineKeyboardButton(
        text="➕ Создать мероприятие", 
        callback_data="admin_event_create"
    )])
    
    if events:
        keyboard.append([InlineKeyboardButton(text="📋 Управление мероприятиями:", callback_data="dummy")])
        
        for event in events:
            status = "🟢" if event['is_active'] else "🔴"
            participants = event.get('participant_count', 0)
            name = event['name'][:25] + "..." if len(event['name']) > 25 else event['name']
            
            keyboard.append([InlineKeyboardButton(
                text=f"{status} {name} ({participants} чел.)",
                callback_data=f"admin_event_manage_{event['id']}"
            )])
    
    keyboard.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_events_refresh"),
        InlineKeyboardButton(text="⬅️ Админ панель", callback_data="admin_panel")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_event_manage_keyboard(event_id, is_active=True):
    """Клавиатура для управления конкретным мероприятием"""
    keyboard = [
        [InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"admin_event_edit_name_{event_id}")],
        [InlineKeyboardButton(text="📝 Изменить описание", callback_data=f"admin_event_edit_desc_{event_id}")],
    ]
    
    if is_active:
        keyboard.append([InlineKeyboardButton(
            text="🔴 Деактивировать", 
            callback_data=f"admin_event_deactivate_{event_id}"
        )])
    else:
        keyboard.append([InlineKeyboardButton(
            text="🟢 Активировать", 
            callback_data=f"admin_event_activate_{event_id}"
        )])
    
    keyboard.append([
        InlineKeyboardButton(text="⬅️ К списку", callback_data="admin_events_list"),
        InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"admin_event_delete_{event_id}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def format_event_info(event, participant_count=None):
    """Форматирование информации о мероприятии"""
    if participant_count is None:
        participant_count = event.get('participant_count', 0)
    
    status = "🟢 Активно" if event['is_active'] else "🔴 Неактивно"
    created_date = event['created_at'][:10] if event['created_at'] else "Неизвестно"
    
    return f"""
🎉 **{event['name']}**

📋 **Описание:**
{event['description']}

👥 **Участников:** {participant_count}
📅 **Создано:** {created_date}
📊 **Статус:** {status}
"""

# === ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ ===

@router.message(Command("events"))
async def events_list_command(message: Message):
    """Список мероприятий"""
    from handlers.menu import edit_or_send_message
    user = await db.get_user(message.from_user.id)
    
    if not user or user['verification_status'] != 'approved':
        await edit_or_send_message(message, "❌ Эта функция доступна только верифицированным пользователям.")
        return
    
    events = await db.get_active_events()
    
    await edit_or_send_message(
        message,
        f"🎉 **Мероприятия ({len(events)})**\n\n"
        "Выбери мероприятие для подробной информации:",
        reply_markup=get_events_list_keyboard(events, user['id'])
    )

@router.message(Command("my_events"))
async def my_events_command(message: Message):
    """Мои мероприятия"""
    from handlers.menu import edit_or_send_message
    user = await db.get_user(message.from_user.id)
    
    if not user or user['verification_status'] != 'approved':
        await edit_or_send_message(message, "❌ Эта функция доступна только верифицированным пользователям.")
        return
    
    my_events = await db.get_user_events(user['id'])
    
    if not my_events:
        await edit_or_send_message(
            message,
            "📭 **У тебя пока нет мероприятий**\n\n"
            "Используй /events чтобы найти интересные события!"
        )
        return
    
    events_text = []
    for event in my_events:
        joined_date = event['joined_at'][:10] if event['joined_at'] else "Неизвестно"
        events_text.append(f"🎉 **{event['name']}**\n📅 Записался: {joined_date}")
    
    await edit_or_send_message(
        message,
        f"🎉 **Твои мероприятия ({len(my_events)})**\n\n" + 
        "\n\n".join(events_text)
    )

# === CALLBACK ОБРАБОТЧИКИ ===

@router.callback_query(F.data == "events_list")
@router.callback_query(F.data == "events_refresh")
async def events_list_callback(callback: CallbackQuery):
    """Показать список мероприятий"""
    user = await db.get_user(callback.from_user.id)
    
    if not user or user['verification_status'] != 'approved':
        await callback.answer("❌ Доступно только верифицированным пользователям.", show_alert=True)
        return
    
    events = await db.get_active_events()
    
    await callback.message.edit_text(
        f"🎉 **Мероприятия ({len(events)})**\n\n"
        "Выбери мероприятие для подробной информации:",
        reply_markup=get_events_list_keyboard(events, user['id'])
    )

@router.callback_query(F.data.startswith("event_view_"))
async def event_view_callback(callback: CallbackQuery):
    """Просмотр мероприятия"""
    event_id = int(callback.data.split("_")[2])
    user = await db.get_user(callback.from_user.id)
    
    if not user or user['verification_status'] != 'approved':
        await callback.answer("❌ Доступно только верифицированным пользователям.", show_alert=True)
        return
    
    event = await db.get_event_by_id(event_id)
    if not event or not event['is_active']:
        await callback.answer("❌ Мероприятие не найдено или неактивно.", show_alert=True)
        return
    
    is_joined = await db.is_user_joined_event(user['id'], event_id)
    event_text = format_event_info(event)
    
    await callback.message.edit_text(
        event_text,
        reply_markup=get_event_actions_keyboard(event_id, is_joined)
    )

@router.callback_query(F.data.startswith("event_join_"))
async def event_join_callback(callback: CallbackQuery):
    """Записаться на мероприятие"""
    event_id = int(callback.data.split("_")[2])
    user = await db.get_user(callback.from_user.id)
    
    if not user or user['verification_status'] != 'approved':
        await callback.answer("❌ Доступно только верифицированным пользователям.", show_alert=True)
        return
    
    event = await db.get_event_by_id(event_id)
    if not event or not event['is_active']:
        await callback.answer("❌ Мероприятие недоступно.", show_alert=True)
        return
    
    await db.join_event(user['id'], event_id)
    
    # Обновляем информацию о мероприятии
    updated_event = await db.get_event_by_id(event_id)
    event_text = format_event_info(updated_event)
    
    await callback.message.edit_text(
        event_text,
        reply_markup=get_event_actions_keyboard(event_id, True)
    )
    
    await callback.answer("✅ Ты записался на мероприятие!", show_alert=False)
    logger.info(f"User {user['id']} joined event {event_id}")

@router.callback_query(F.data.startswith("event_leave_"))
async def event_leave_callback(callback: CallbackQuery):
    """Отписаться от мероприятия"""
    event_id = int(callback.data.split("_")[2])
    user = await db.get_user(callback.from_user.id)
    
    if not user or user['verification_status'] != 'approved':
        await callback.answer("❌ Доступно только верифицированным пользователям.", show_alert=True)
        return
    
    await db.leave_event(user['id'], event_id)
    
    # Обновляем информацию о мероприятии
    updated_event = await db.get_event_by_id(event_id)
    if updated_event:
        event_text = format_event_info(updated_event)
        await callback.message.edit_text(
            event_text,
            reply_markup=get_event_actions_keyboard(event_id, False)
        )
    
    await callback.answer("❌ Ты отписался от мероприятия.", show_alert=False)
    logger.info(f"User {user['id']} left event {event_id}")

@router.callback_query(F.data == "events_close")
async def events_close_callback(callback: CallbackQuery):
    """Закрыть меню мероприятий"""
    await callback.message.edit_text("✅ Меню мероприятий закрыто.")

@router.callback_query(F.data == "no_events")
async def no_events_callback(callback: CallbackQuery):
    """Заглушка для пустого списка"""
    await callback.answer("Мероприятий пока нет", show_alert=False)

# === АДМИНСКИЕ КОМАНДЫ ===

@router.message(Command("events_admin"))
async def admin_events_command(message: Message):
    """Админское управление мероприятиями"""
    # Импортируем функцию для правильного управления сообщениями
    from handlers.menu import edit_or_send_message
    
    if not is_admin(message):
        await edit_or_send_message(message, "❌ У вас нет прав администратора.")
        return
    
    events = await db.get_all_events()
    
    await edit_or_send_message(
        message,
        f"🔧 **Управление мероприятиями ({len(events)})**\n\n"
        "Выберите действие:",
        reply_markup=get_admin_events_keyboard(events)
    )

@router.callback_query(F.data == "admin_events_list")
@router.callback_query(F.data == "admin_events_refresh")
async def admin_events_list_callback(callback: CallbackQuery):
    """Список мероприятий для админа"""
    if not is_admin(callback):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    events = await db.get_all_events()
    
    await callback.message.edit_text(
        f"🔧 **Управление мероприятиями ({len(events)})**\n\n"
        "Выберите действие:",
        reply_markup=get_admin_events_keyboard(events)
    )

@router.callback_query(F.data == "admin_event_create")
async def admin_event_create_callback(callback: CallbackQuery, state: FSMContext):
    """Начать создание мероприятия"""
    if not is_admin(callback):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    # Очищаем предыдущие FSM состояния (админ режим должен остаться)
    try:
        bot = callback.bot
        dispatcher = getattr(bot, 'dispatcher', None)
        if dispatcher and hasattr(dispatcher, 'storage'):
            storage = dispatcher.storage
            from aiogram.fsm.storage.base import StorageKey
            key = StorageKey(bot.id, callback.from_user.id, callback.from_user.id)
            
            await storage.set_state(key, None)
            await storage.set_data(key, {})
    except Exception:
        pass
    
    await callback.message.edit_text(
        "➕ **Создание мероприятия**\n\n"
        "Все предыдущие операции сброшены.\n"
        "Введите название мероприятия (до 100 символов):"
    )
    await state.set_state(EventStates.name)

@router.message(EventStates.name)
async def process_event_name(message: Message, state: FSMContext):
    """Обработка названия мероприятия"""
    name = message.text.strip()
    
    if len(name) < 5 or len(name) > 100:
        await message.answer("❌ Название должно содержать от 5 до 100 символов. Попробуйте еще раз:")
        return
    
    await state.update_data(name=name)
    await message.answer(
        f"✅ Название: **{name}**\n\n"
        "Теперь введите описание мероприятия (до 1000 символов):"
    )
    await state.set_state(EventStates.description)

@router.message(EventStates.description)
async def process_event_description(message: Message, state: FSMContext):
    """Обработка описания мероприятия"""
    description = message.text.strip()
    
    if len(description) < 10 or len(description) > 1000:
        await message.answer("❌ Описание должно содержать от 10 до 1000 символов. Попробуйте еще раз:")
        return
    
    event_data = await state.get_data()
    
    # Создаем мероприятие
    event_id = await db.create_event(
        name=event_data['name'],
        description=description,
        created_by=message.from_user.id
    )
    
    await message.answer(
        f"✅ **Мероприятие создано!**\n\n"
        f"🎉 **{event_data['name']}**\n\n"
        f"📋 **Описание:**\n{description}\n\n"
        f"ID: {event_id}"
    )
    
    await state.clear()
    logger.info(f"Admin {message.from_user.id} created event {event_id}")

@router.callback_query(F.data.startswith("admin_event_manage_"))
async def admin_event_manage_callback(callback: CallbackQuery):
    """Управление мероприятием"""
    event_id = int(callback.data.split("_")[3])
    
    if not is_admin(callback):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    event = await db.get_event_by_id(event_id)
    if not event:
        await callback.answer("❌ Мероприятие не найдено.", show_alert=True)
        return
    
    event_text = format_event_info(event)
    
    await callback.message.edit_text(
        f"🔧 **Управление мероприятием**\n\n{event_text}",
        reply_markup=get_admin_event_manage_keyboard(event_id, event['is_active'])
    )

@router.callback_query(F.data.startswith("admin_event_activate_"))
async def admin_event_activate_callback(callback: CallbackQuery):
    """Активировать мероприятие"""
    event_id = int(callback.data.split("_")[3])
    
    if not is_admin(callback):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    await db.update_event(event_id, is_active=True)
    
    event = await db.get_event_by_id(event_id)
    event_text = format_event_info(event)
    
    await callback.message.edit_text(
        f"🔧 **Управление мероприятием**\n\n{event_text}",
        reply_markup=get_admin_event_manage_keyboard(event_id, True)
    )
    
    await callback.answer("🟢 Мероприятие активировано!", show_alert=False)

@router.callback_query(F.data.startswith("admin_event_deactivate_"))
async def admin_event_deactivate_callback(callback: CallbackQuery):
    """Деактивировать мероприятие"""
    event_id = int(callback.data.split("_")[3])
    
    if not is_admin(callback):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    await db.update_event(event_id, is_active=False)
    
    event = await db.get_event_by_id(event_id)
    event_text = format_event_info(event)
    
    await callback.message.edit_text(
        f"🔧 **Управление мероприятием**\n\n{event_text}",
        reply_markup=get_admin_event_manage_keyboard(event_id, False)
    )
    
    await callback.answer("🔴 Мероприятие деактивировано!", show_alert=False)
