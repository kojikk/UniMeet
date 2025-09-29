from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

from database import Database
from config import DATABASE_URL
from utils import is_admin

router = Router()
db = Database(DATABASE_URL)

def get_main_menu_keyboard(user_status: str = None, is_user_admin: bool = False):
    """Главное меню в зависимости от статуса пользователя"""
    keyboard = []
    
    if user_status == 'approved':
        # Меню для верифицированных пользователей
        keyboard = [
            [KeyboardButton(text="👤 Моя анкета"), KeyboardButton(text="✏️ Редактировать")],
            [KeyboardButton(text="🔍 Поиск людей"), KeyboardButton(text="🎉 Мероприятия")],
        ]
        
        if is_user_admin:
            keyboard.append([KeyboardButton(text="🔧 Админ панель")])
            
    elif user_status == 'pending':
        # Меню для пользователей на модерации
        keyboard = [
            [KeyboardButton(text="👤 Моя анкета")],
            [KeyboardButton(text="ℹ️ Статус верификации")]
        ]
        
        if is_user_admin:
            keyboard.append([KeyboardButton(text="🔧 Админ панель")])
            
    elif user_status == 'rejected':
        # Меню для пользователей с отклоненной заявкой
        keyboard = [
            [KeyboardButton(text="👤 Моя анкета"), KeyboardButton(text="✏️ Изменить анкету")],
            [KeyboardButton(text="📸 Повторная верификация")]
        ]
        
        if is_user_admin:
            keyboard.append([KeyboardButton(text="🔧 Админ панель")])
            
    else:
        # Меню для новых пользователей
        keyboard = [
            [KeyboardButton(text="🚀 Создать анкету")],
            [KeyboardButton(text="ℹ️ О боте")]
        ]
        
        if is_user_admin:
            keyboard.append([KeyboardButton(text="🔧 Админ панель")])
    
    # Общие кнопки для всех
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
async def create_profile_menu(message: Message):
    """Создание анкеты через меню"""
    from handlers.registration import start_command
    await start_command(message, None)

@router.message(F.text == "👤 Моя анкета")
async def view_profile_menu(message: Message):
    """Просмотр анкеты через меню"""
    from handlers.registration import view_profile
    await view_profile(message)

@router.message(F.text == "✏️ Редактировать")
@router.message(F.text == "✏️ Изменить анкету")
async def edit_profile_menu(message: Message):
    """Редактирование анкеты через меню"""
    from handlers.registration import edit_profile_command
    await edit_profile_command(message, None)

@router.message(F.text == "🔧 Админ панель")
async def admin_panel_menu(message: Message):
    """Админ панель через меню"""
    if not is_admin(message):
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    from handlers.admin import admin_panel_command
    await admin_panel_command(message)

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
    
    status_text = {
        'not_requested': '🆕 Верификация не запрошена',
        'pending': '⏳ На рассмотрении у администраторов',
        'approved': '✅ Верификация пройдена',
        'rejected': '❌ Заявка отклонена'
    }
    
    status = user['verification_status']
    await message.answer(
        f"ℹ️ **Статус верификации**\n\n"
        f"Текущий статус: {status_text.get(status, 'Неизвестно')}\n\n"
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
    
    if user and user['verification_status'] == 'approved':
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
    status = user['verification_status'] if user else None
    is_user_admin = is_admin(message)
    
    await message.answer(
        "📋 **Главное меню**\n\n"
        "Выбери действие из меню ниже или используй кнопки:",
        reply_markup=get_main_menu_keyboard(status, is_user_admin)
    )

async def update_user_menu(message: Message, user_status: str):
    """Обновить меню пользователя"""
    is_user_admin = is_admin(message)
    
    await message.answer(
        "📋 Меню обновлено!",
        reply_markup=get_main_menu_keyboard(user_status, is_user_admin)
    )
