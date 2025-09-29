from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import Database
from config import DATABASE_URL
from utils import is_admin

router = Router()
db = Database(DATABASE_URL)

def determine_user_state(user):
    """Определить состояние пользователя на основе данных"""
    if not user or not user.get('name'):
        return 'new'  # Новый пользователь
    
    verification_status = user.get('verification_status', 'not_requested')
    
    if verification_status == 'not_requested':
        return 'draft'  # Анкета создана, но не подана на верификацию
    elif verification_status == 'pending':
        return 'pending'  # На модерации
    elif verification_status == 'approved':
        return 'approved'  # Верифицирован
    elif verification_status == 'rejected':
        return 'rejected'  # Отклонен
    else:
        return 'new'  # Неизвестное состояние = новый

def get_main_menu_keyboard(user_state: str = 'new', is_user_admin: bool = False, admin_mode: bool = False):
    """Главное меню в зависимости от состояния пользователя"""
    keyboard = []
    
    if admin_mode:
        # Админское меню
        keyboard = [
            [KeyboardButton(text="📋 Заявки на верификацию")],
            [KeyboardButton(text="🎉 Управление мероприятиями")],
            [KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="🚪 Выйти из админки")]
        ]
        
    else:
        # Пользовательское меню в зависимости от состояния
        if user_state == 'new':
            # Новый пользователь
            keyboard = [
                [KeyboardButton(text="🚀 Создать анкету")],
                [KeyboardButton(text="ℹ️ О боте")]
            ]
            
        elif user_state == 'draft':
            # Анкета создана, но не подана на верификацию
            keyboard = [
                [KeyboardButton(text="👤 Моя анкета"), KeyboardButton(text="✏️ Редактировать")],
                [KeyboardButton(text="📤 Подать на верификацию")]
            ]
            
        elif user_state == 'pending':
            # На модерации
            keyboard = [
                [KeyboardButton(text="👤 Моя анкета")],
                [KeyboardButton(text="ℹ️ Статус верификации")]
            ]
                
        elif user_state == 'approved':
            # Верифицирован - полный доступ
            keyboard = [
                [KeyboardButton(text="👤 Моя анкета"), KeyboardButton(text="✏️ Редактировать")],
                [KeyboardButton(text="🔍 Поиск людей"), KeyboardButton(text="🎉 Мероприятия")],
            ]
                
        elif user_state == 'rejected':
            # Отклонен - нужны изменения
            keyboard = [
                [KeyboardButton(text="👤 Моя анкета"), KeyboardButton(text="✏️ Редактировать")],
                [KeyboardButton(text="📸 Повторная верификация")]
            ]
        
        # Админская кнопка для всех админов независимо от состояния
        if is_user_admin:
            keyboard.append([KeyboardButton(text="🔧 Админ панель")])
        
        # Общие кнопки для всех (кроме админского режима)
        keyboard.append([KeyboardButton(text="❓ Помощь")])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите действие..."
    )

def get_inline_menu_keyboard(user_status: str = None, is_user_admin: bool = False):
    """Inline меню для быстрых действий"""
    keyboard = []
    
    if user_status == 'approved':
        keyboard = [
            [
                InlineKeyboardButton(text="👤 Анкета", callback_data="menu_profile"),
                InlineKeyboardButton(text="✏️ Изменить", callback_data="menu_edit")
            ],
            [
                InlineKeyboardButton(text="🔍 Поиск", callback_data="menu_search"),
                InlineKeyboardButton(text="🎉 События", callback_data="menu_events")
            ]
        ]
    elif user_status == 'pending':
        keyboard = [
            [InlineKeyboardButton(text="👤 Моя анкета", callback_data="menu_profile")],
            [InlineKeyboardButton(text="⏳ Статус", callback_data="menu_status")]
        ]
    elif user_status == 'rejected':
        keyboard = [
            [InlineKeyboardButton(text="✏️ Изменить анкету", callback_data="menu_edit")],
            [InlineKeyboardButton(text="📸 Новое фото", callback_data="menu_reverify")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton(text="🚀 Начать", callback_data="menu_start")]
        ]
    
    if is_user_admin:
        keyboard.append([InlineKeyboardButton(text="🔧 Админ", callback_data="menu_admin")])
    
    keyboard.append([InlineKeyboardButton(text="❓ Помощь", callback_data="menu_help")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(F.text == "🚀 Создать анкету")
async def create_profile_menu(message: Message, state: FSMContext):
    """Создание анкеты через меню"""
    from handlers.registration import start_command
    await start_command(message, state)

@router.message(F.text == "👤 Моя анкета")
async def view_profile_menu(message: Message):
    """Просмотр анкеты через меню"""
    from handlers.registration import view_profile
    await view_profile(message)

@router.message(F.text == "✏️ Редактировать")
@router.message(F.text.in_(["✏️ Редактировать", "✏️ Изменить анкету"]))
async def edit_profile_menu(message: Message, state: FSMContext):
    """Редактирование анкеты через меню (унификация названий кнопок)"""
    from handlers.registration import edit_profile_command
    await edit_profile_command(message, state)

@router.message(F.text == "📤 Подать на верификацию")
async def submit_for_verification_menu(message: Message):
    """Подача анкеты на верификацию из состояния draft"""
    user = await db.get_user(message.from_user.id)
    
    if not user or not user.get('name'):
        await message.answer("❌ Сначала создай анкету!")
        return
        
    if user.get('verification_status') != 'not_requested':
        await message.answer("❌ Анкета уже подана на верификацию или обработана.")
        return
    
    await message.answer(
        "📸 **Верификация аккаунта**\n\n"
        "Для подтверждения того, что ты студент, отправь фотографию "
        "своего студенческого билета.\n\n"
        "**Требования к фото:**\n"
        "• Четкое изображение\n"
        "• Видны основные данные\n"
        "• Хорошее освещение\n\n"
        "Отправь фото:"
    )
    
    from handlers.states import VerificationStates
    from aiogram.fsm.context import FSMContext
    state = FSMContext.get_instance()
    await state.set_state(VerificationStates.student_card_photo)

# Админская панель теперь обрабатывается в handlers/admin_mode.py

@router.message(F.text == "🔍 Поиск людей")
async def search_people_menu(message: Message):
    """Поиск людей через меню"""
    user = await db.get_user(message.from_user.id)
    
    if not user or user['verification_status'] != 'approved':
        await message.answer("❌ Эта функция доступна только верифицированным пользователям.")
        return
    
    # Проверяем участие в мероприятиях
    events_count = await db.get_user_events_count(user['id'])
    
    if events_count == 0:
        await message.answer(
            "❌ **Для поиска людей нужно участие в мероприятиях**\n\n"
            "Сначала запишись хотя бы на одно мероприятие:\n"
            "🎉 Используй кнопку **Мероприятия**\n\n"
            "Это поможет находить людей с общими интересами! 🤝"
        )
        return
    
    await message.answer(
        f"🔍 **Поиск людей**\n\n"
        f"👥 Ты участвуешь в {events_count} мероприятии(ях)\n\n"
        "Функция поиска анкет будет доступна в следующем обновлении!\n"
        "Скоро ты сможешь:\n"
        "• Просматривать анкеты других студентов\n"
        "• Ставить лайки и дизлайки\n"
        "• Находить людей с общими мероприятиями\n\n"
        "Следи за обновлениями! 🚀"
    )

@router.message(F.text == "🎉 Мероприятия")
async def events_menu(message: Message):
    """Мероприятия через меню"""
    from handlers.events import events_list_command
    await events_list_command(message)

@router.message(F.text == "📸 Повторная верификация")
async def reverify_menu(message: Message):
    """Повторная верификация через меню"""
    from handlers.registration import resend_verification_callback
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.base import StorageKey
    
    # Создаем фейковый callback для переиспользования логики
    user = await db.get_user(message.from_user.id)
    
    if not user or user['verification_status'] != 'rejected':
        await message.answer("❌ Повторная верификация доступна только при отклоненной заявке.")
        return
    
    await message.answer(
        "📸 **Повторная верификация**\n\n"
        "Отправь новое фото со своим студенческим билетом:\n\n"
        "**Убедись, что:**\n"
        "• Фото четкое и разборчивое\n"
        "• Видны все данные студбилета\n"
        "• Данные соответствуют твоей анкете\n\n"
        "После отправки фото твоя заявка снова попадет на рассмотрение к администраторам."
    )
    
    # Устанавливаем состояние для ожидания фото
    from aiogram import Bot
    from handlers.states import VerificationStates
    bot = Bot.get_current()
    storage = bot.session.middleware.storage if hasattr(bot.session, 'middleware') else None
    
    if storage:
        key = StorageKey(bot.id, message.from_user.id, message.from_user.id)
        await storage.set_state(key, VerificationStates.student_card_photo)

@router.message(F.text == "ℹ️ Статус верификации")
async def status_menu(message: Message):
    """Проверка статуса верификации через меню"""
    user = await db.get_user(message.from_user.id)
    
    if not user:
        await message.answer("❌ У тебя пока нет анкеты.")
        return
    
    # Используем новую логику состояний
    user_state = determine_user_state(user)
    
    await message.answer(
        f"ℹ️ **Статус верификации**\n\n"
        f"Текущее состояние: {get_status_emoji(user_state)} {get_status_text(user_state)}\n\n"
        f"📅 Анкета создана: {user['created_at'][:10] if user['created_at'] else 'Неизвестно'}"
    )

@router.message(F.text == "ℹ️ О боте")
async def about_bot_menu(message: Message):
    """Информация о боте через меню"""
    await message.answer(
        "🎓 **О UniMeetingBot**\n\n"
        "Привет! Я бот для знакомств студентов университета.\n\n"
        "**Что я умею:**\n"
        "• Создавать анкеты студентов\n"
        "• Верифицировать пользователей\n"
        "• Помогать находить новых друзей\n\n"
        "**Скоро добавлю:**\n"
        "• Систему мероприятий\n"
        "• Поиск по интересам\n"
        "• Рекомендации друзей\n\n"
        "Для начала создай свою анкету кнопкой 'Создать анкету' 🚀"
    )

@router.message(F.text == "❓ Помощь")
async def help_menu(message: Message):
    """Помощь через меню"""
    user = await db.get_user(message.from_user.id)
    admin_text = "\n\n🔧 **Админские команды:**\n/admin_panel - панель администратора\n/pending - заявки на верификацию" if is_admin(message) else ""
    
    # Используем новую логику состояний
    user_state = determine_user_state(user) if user else 'new'
    
    if user_state == 'approved':
        await message.answer(
            "❓ **Помощь**\n\n"
            "**Доступные функции:**\n"
            "👤 Моя анкета - посмотреть свою анкету\n"
            "✏️ Редактировать - изменить данные\n"
            "🔍 Поиск людей - найти новых друзей\n"
            "🎉 Мероприятия - студенческие события\n\n"
            "**Команды:**\n"
            "/start - главное меню\n"
            "/profile - показать анкету\n"
            "/edit - редактировать\n\n"
            "По вопросам обращайтесь к администраторам." + admin_text
        )
    elif user and user['verification_status'] == 'pending':
        await message.answer(
            "❓ **Помощь**\n\n"
            "⏳ Твоя анкета на рассмотрении у администраторов.\n\n"
            "**Доступные функции:**\n"
            "👤 Моя анкета - посмотреть анкету\n"
            "ℹ️ Статус верификации - проверить статус\n\n"
            "**Команды:**\n"
            "/start - главное меню\n"
            "/profile - показать анкету\n\n"
            "Дождись подтверждения, чтобы получить доступ ко всем функциям!" + admin_text
        )
    elif user and user['verification_status'] == 'rejected':
        await message.answer(
            "❓ **Помощь**\n\n"
            "❌ Твоя заявка была отклонена.\n\n"
            "**Доступные функции:**\n"
            "✏️ Изменить анкету - исправить данные\n"
            "📸 Повторная верификация - отправить новое фото\n\n"
            "**Команды:**\n"
            "/start - главное меню\n"
            "/edit - редактировать анкету\n\n"
            "После изменений подай заявку повторно!" + admin_text
        )
    else:
        await message.answer(
            "❓ **Помощь**\n\n"
            "Добро пожаловать в UniMeetingBot!\n\n"
            "**Для начала работы:**\n"
            "🚀 Создать анкету - заполнить профиль\n"
            "ℹ️ О боте - узнать больше\n\n"
            "**Команды:**\n"
            "/start - начать регистрацию\n\n"
            "После создания анкеты пройди верификацию для доступа ко всем функциям!" + admin_text
        )

# Inline callback обработчики
@router.callback_query(F.data == "menu_profile")
async def inline_profile_callback(callback: CallbackQuery):
    """Просмотр профиля через inline"""
    from handlers.registration import view_profile
    await view_profile(callback.message)

@router.callback_query(F.data == "menu_edit")
async def inline_edit_callback(callback: CallbackQuery):
    """Редактирование через inline"""
    from handlers.registration import edit_profile_command
    await edit_profile_command(callback.message, None)

@router.callback_query(F.data == "menu_admin")
async def inline_admin_callback(callback: CallbackQuery):
    """Админ панель через inline"""
    if not is_admin(callback):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    from handlers.admin import admin_panel_callback
    await admin_panel_callback(callback)

@router.callback_query(F.data == "menu_search")
async def inline_search_callback(callback: CallbackQuery):
    """Поиск через inline"""
    user = await db.get_user(callback.from_user.id)
    
    if not user or user['verification_status'] != 'approved':
        await callback.answer("❌ Доступно только верифицированным пользователям.", show_alert=True)
        return
    
    # Проверяем участие в мероприятиях
    events_count = await db.get_user_events_count(user['id'])
    
    if events_count == 0:
        await callback.answer("❌ Для поиска людей нужно участие хотя бы в одном мероприятии!", show_alert=True)
        return
    
    await callback.answer("🔍 Функция поиска будет добавлена в следующем обновлении!", show_alert=True)

@router.callback_query(F.data == "menu_events")
async def inline_events_callback(callback: CallbackQuery):
    """События через inline"""
    user = await db.get_user(callback.from_user.id)
    
    if not user or user['verification_status'] != 'approved':
        await callback.answer("❌ Доступно только верифицированным пользователям.", show_alert=True)
        return
    
    from handlers.events import events_list_callback
    await events_list_callback(callback)

@router.callback_query(F.data == "menu_help")
async def inline_help_callback(callback: CallbackQuery):
    """Помощь через inline"""
    await help_menu(callback.message)

@router.callback_query(F.data == "menu_start")
async def inline_start_callback(callback: CallbackQuery):
    """Начать через inline"""
    from handlers.registration import start_command
    await start_command(callback.message, None)

@router.callback_query(F.data == "menu_status")
async def inline_status_callback(callback: CallbackQuery):
    """Статус через inline"""
    await status_menu(callback.message)

@router.message(Command("menu"))
async def show_menu_command(message: Message):
    """Показать меню"""
    user = await db.get_user(message.from_user.id)
    # Используем новую логику состояний
    user_state = determine_user_state(user) if user else 'new'
    is_user_admin = is_admin(message)
    from handlers.admin import is_in_admin_mode
    admin_mode = is_in_admin_mode(message.from_user.id)
    
    await message.answer(
        "📋 **Главное меню**\n\n"
        "Выбери действие из меню ниже или используй кнопки:",
        reply_markup=get_main_menu_keyboard(user_state, is_user_admin, admin_mode)
    )

async def update_user_menu(message: Message, user_state: str, user_id: int = None):
    """Обновить меню пользователя с правильным определением админа"""
    from handlers.admin import is_in_admin_mode
    
    # Если user_id не передан, используем из message
    actual_user_id = user_id if user_id else message.from_user.id
    
    # Для проверки админа создаем правильный объект
    class FakeMessage:
        def __init__(self, from_user_data):
            self.from_user = from_user_data
    
    # Получаем данные пользователя из Telegram для проверки админа
    from aiogram import Bot
    bot = Bot.get_current()
    try:
        user_info = await bot.get_chat(actual_user_id)
        fake_message = FakeMessage(user_info)
        is_user_admin = is_admin(fake_message)
    except Exception:
        # Если не удалось получить данные, используем исходную логику
        is_user_admin = is_admin(message)
    
    admin_mode = is_in_admin_mode(actual_user_id)
    
    # Логируем для отладки
    print(f"🔍 DEBUG update_user_menu:")
    print(f"   user_id: {message.from_user.id}")
    print(f"   username: {message.from_user.username}")
    print(f"   user_state: {user_state}")
    print(f"   is_admin: {is_user_admin}")
    print(f"   admin_mode: {admin_mode}")
    
    # Дополнительная диагностика админского статуса
    from config import ADMIN_IDS, ADMIN_USERNAMES
    print(f"   ADMIN_IDS: {ADMIN_IDS}")
    print(f"   ADMIN_USERNAMES: {ADMIN_USERNAMES}")
    print(f"   user_id in ADMIN_IDS: {message.from_user.id in ADMIN_IDS}")
    username_lower = message.from_user.username.lower() if message.from_user.username else None
    print(f"   username_lower: {username_lower}")
    print(f"   username in ADMIN_USERNAMES: {username_lower and username_lower in ADMIN_USERNAMES}")
    
    await message.answer(
        "📋 Меню обновлено!",
        reply_markup=get_main_menu_keyboard(user_state, is_user_admin, admin_mode)
    )

def get_status_emoji(user_state: str) -> str:
    """Получить эмодзи для состояния пользователя"""
    status_emojis = {
        'new': '⚫',  # Новый
        'draft': '⚪',  # Черновик
        'pending': '🟡',  # На модерации
        'approved': '🟢',  # Верифицирован
        'rejected': '🔴'  # Отклонен
    }
    return status_emojis.get(user_state, '⚪')

def get_status_text(user_state: str) -> str:
    """Получить текст для состояния пользователя"""
    status_texts = {
        'new': 'Анкета не создана',
        'draft': 'Черновик (не подана на верификацию)', 
        'pending': 'На модерации',
        'approved': 'Верифицирована ✅',
        'rejected': 'Требует изменений'
    }
    return status_texts.get(user_state, 'Неизвестное состояние')
