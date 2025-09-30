from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import Database
from config import DATABASE_URL
from utils import is_admin

router = Router()
db = Database(DATABASE_URL)

# Словарь для хранения последних сообщений бота для каждого пользователя  
last_bot_messages = {}
# Словарь для отслеживания типа предыдущего сообщения (True = с фото, False = текст)
last_message_has_photo = {}

# Альтернативный подход - редактирование вместо удаления
async def edit_or_send_message(message: Message, text: str, reply_markup=None, photo=None):
    """Отредактировать предыдущее сообщение или отправить новое"""
    user_id = message.from_user.id
    
    print(f"🔍 DEBUG edit_or_send_message: user_id={user_id}, photo={'есть' if photo else 'нет'}")
    print(f"🔍 Сохраненные сообщения: {last_bot_messages}")
    
    # Пытаемся удалить сообщение пользователя
    try:
        await message.delete()
        print("✅ Сообщение пользователя удалено")
    except Exception as e:
        print(f"❌ Не удалось удалить сообщение пользователя: {e}")
    
    # Если есть предыдущее сообщение бота, пытаемся его отредактировать
    if user_id in last_bot_messages:
        bot_message_id = last_bot_messages[user_id]
        previous_had_photo = last_message_has_photo.get(user_id, False)
        print(f"🔄 Пытаемся отредактировать сообщение с ID: {bot_message_id}")
        print(f"📊 Предыдущее сообщение было {'с фото' if previous_had_photo else 'текстовое'}")
        print(f"📊 Новое сообщение будет {'с фото' if photo else 'текстовое'}")
        
        # Определяем, можно ли редактировать или нужно удалять/пересоздавать
        can_edit = not photo and not previous_had_photo  # Только текст → текст можно редактировать
        
        try:
            if can_edit:
                print("📝 Редактирование: изменяем текст (текст→текст)")
                # Можем отредактировать текст
                await message.bot.edit_message_text(
                    text=text,
                    chat_id=message.chat.id,
                    message_id=bot_message_id,
                    reply_markup=reply_markup
                )
                print("✅ Текст сообщения отредактирован")
                # Возвращаем фейковый объект с существующим ID
                class FakeMessage:
                    def __init__(self, message_id):
                        self.message_id = message_id
                sent_message = FakeMessage(bot_message_id)
                
                # Обновляем тип сообщения
                last_message_has_photo[user_id] = bool(photo)
                print(f"💾 Тип сообщения обновлен: {'фото' if photo else 'текст'}")
                return sent_message
                
            else:
                print(f"🔄 Замена: удаляем старое и отправляем новое ({'фото' if photo else 'текст'})")
                # Нужно удалить старое и отправить новое (фото↔текст или фото↔фото)
                await message.bot.delete_message(message.chat.id, bot_message_id)
                
                if photo:
                    sent_message = await message.answer_photo(photo=photo, caption=text, reply_markup=reply_markup)
                    print(f"✅ Новое сообщение с фото отправлено, ID: {sent_message.message_id}")
                else:
                    sent_message = await message.answer(text, reply_markup=reply_markup)
                    print(f"✅ Новое текстовое сообщение отправлено, ID: {sent_message.message_id}")
                
                # Обновляем ID и тип в словарях
                last_bot_messages[user_id] = sent_message.message_id
                last_message_has_photo[user_id] = bool(photo)
                print(f"💾 ID обновлен: {sent_message.message_id}, тип: {'фото' if photo else 'текст'}")
                return sent_message
            
        except Exception as e:
            print(f"❌ Не удалось отредактировать сообщение: {e}")
            # Если не удалось отредактировать, отправляем новое (код ниже)
            # Удаляем из словарей старые данные
            if user_id in last_bot_messages:
                del last_bot_messages[user_id]
            if user_id in last_message_has_photo:
                del last_message_has_photo[user_id]
    
    # Отправляем новое сообщение
    print("📤 Отправляем новое сообщение")
    if photo:
        sent_message = await message.answer_photo(photo=photo, caption=text, reply_markup=reply_markup)
        print(f"✅ Новое сообщение с фото отправлено, ID: {sent_message.message_id}")
    else:
        sent_message = await message.answer(text, reply_markup=reply_markup)
        print(f"✅ Новое текстовое сообщение отправлено, ID: {sent_message.message_id}")
    
    # Сохраняем ID сообщения и его тип
    last_bot_messages[user_id] = sent_message.message_id
    last_message_has_photo[user_id] = bool(photo)
    print(f"💾 Сохранен новый ID: {sent_message.message_id}, тип: {'фото' if photo else 'текст'}")
    print(f"📊 Итоговые сохраненные сообщения: {last_bot_messages}")
    print(f"📊 Типы сообщений: {last_message_has_photo}")
    
    return sent_message

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
            ]
        
        # Админская кнопка для всех админов независимо от состояния
        if is_user_admin:
            keyboard.append([KeyboardButton(text="🔧 Админ панель")])
    
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
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(F.text == "🚀 Создать анкету")
async def create_profile_menu(message: Message, state: FSMContext):
    """Создание анкеты через меню"""
    # Очищаем все предыдущие состояния перед созданием
    from handlers.state_manager import start_user_operation
    
    # Получаем бота из message  
    bot = message.bot
    await start_user_operation(message.from_user.id, bot)
    
    from handlers.registration import start_command
    await start_command(message, state)

async def delete_user_and_bot_messages(message: Message):
    """Удалить сообщение пользователя и предыдущее сообщение бота"""
    user_id = message.from_user.id
    print(f"🔍 DEBUG: Пытаемся удалить сообщения для user_id={user_id}")
    
    # Пытаемся удалить сообщение пользователя
    try:
        await message.delete()
        print(f"✅ Сообщение пользователя удалено")
    except Exception as e:
        print(f"❌ Не удалось удалить сообщение пользователя: {e}")
    
    # Удаляем предыдущее сообщение бота если есть
    if user_id in last_bot_messages:
        bot_message_id = last_bot_messages[user_id]
        print(f"🔍 Найдено предыдущее сообщение бота с ID: {bot_message_id}")
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=bot_message_id
            )
            print(f"✅ Предыдущее сообщение бота удалено")
        except Exception as e:
            print(f"❌ Не удалось удалить сообщение бота: {e}")
        
        # Удаляем из словаря
        del last_bot_messages[user_id]
        print(f"🗑️ ID сообщения удалён из словаря")
    else:
        print(f"ℹ️ Предыдущих сообщений для удаления не найдено")

async def send_and_save_message(message: Message, text: str, reply_markup=None):
    """Отправить сообщение и сохранить его ID"""
    sent_message = await message.answer(text, reply_markup=reply_markup)
    
    # Сохраняем ID отправленного сообщения
    user_id = message.from_user.id
    message_id = sent_message.message_id
    last_bot_messages[user_id] = message_id
    print(f"💾 Сохранён ID сообщения: {message_id} для user_id: {user_id}")
    print(f"📊 Текущие сохранённые сообщения: {last_bot_messages}")
    return sent_message

@router.message(F.text == "👤 Моя анкета")
async def view_profile_menu(message: Message):
    """Просмотр анкеты через меню"""
    try:
        # Получаем профиль и отправляем
        user = await db.get_user(message.from_user.id)
        
        if not user or not user.get('name'):
            # Получаем меню для нового пользователя
            current_menu = get_main_menu_keyboard('new', is_admin(message), admin_mode=False)
            await edit_or_send_message(message, "❌ У тебя пока нет анкеты. Создай её!", reply_markup=current_menu)
            return

        # Форматируем анкету
        status_emoji = get_status_emoji(user.get('verification_status', 'not_requested'))
        status_text = get_status_text(user.get('verification_status', 'not_requested'))
        
        profile_text = f"""👤 **Твоя анкета** {status_emoji}

**Статус:** {status_text}
**Имя:** {user['name']}
**Возраст:** {user['age']} лет
**Курс:** {user['course']}
**Направление:** {user['major']}

**Описание:**
{user['description']}"""
        
        # Получаем текущее меню для сохранения клавиатуры
        user_state = determine_user_state(user)
        is_user_admin = is_admin(message)
        current_menu = get_main_menu_keyboard(user_state, is_user_admin, admin_mode=False)
        
        # Используем новую функцию для редактирования/отправки (она сама удалит и отредактирует)
        if user.get('photo_file_id'):
            await edit_or_send_message(message, profile_text, reply_markup=current_menu, photo=user['photo_file_id'])
        else:
            await edit_or_send_message(message, profile_text, reply_markup=current_menu)
    
    except Exception as e:
        print(f"❌ Ошибка в view_profile_menu: {e}")
        # В случае ошибки отправляем простое сообщение
        await message.answer("❌ Произошла ошибка при загрузке анкеты. Попробуй еще раз.")

@router.message(F.text == "✏️ Редактировать")
@router.message(F.text.in_(["✏️ Редактировать", "✏️ Изменить анкету"]))
async def edit_profile_menu(message: Message, state: FSMContext):
    """Редактирование анкеты через меню (унификация названий кнопок)"""
    # Очищаем все предыдущие состояния перед редактированием
    from handlers.state_manager import start_user_operation
    
    # Получаем бота из message
    bot = message.bot
    await start_user_operation(message.from_user.id, bot)
    
    # Удаляем сообщение пользователя сначала
    try:
        await message.delete()
        print("✅ Сообщение пользователя (редактировать) удалено")
    except Exception as e:
        print(f"❌ Не удалось удалить сообщение пользователя: {e}")
    
    # Уведомляем пользователя о смене режима если он был в админке
    from handlers.admin import is_in_admin_mode
    was_in_admin = is_in_admin_mode(message.from_user.id)
    
    if was_in_admin:
        await message.answer("🔄 **Режим изменен**\n\nВышел из админ-панели для редактирования анкеты.")
    
    from handlers.registration import edit_profile_command
    await edit_profile_command(message, state)

@router.message(F.text == "📤 Подать на верификацию")
async def submit_for_verification_menu(message: Message, state: FSMContext):
    """Подача анкеты на верификацию из состояния draft"""
    # Очищаем все предыдущие состояния
    from handlers.state_manager import start_user_operation
    
    # Получаем бота из message
    bot = message.bot
    await start_user_operation(message.from_user.id, bot)
    
    user = await db.get_user(message.from_user.id)
    
    # Определяем текущее меню
    if not user:
        user_state = 'new'
        current_menu = get_main_menu_keyboard('new', is_admin(message), admin_mode=False)
    else:
        user_state = determine_user_state(user)
        current_menu = get_main_menu_keyboard(user_state, is_admin(message), admin_mode=False)
    
    if not user or not user.get('name'):
        await edit_or_send_message(message, "❌ Сначала создай анкету!", reply_markup=current_menu)
        return
        
    if user.get('verification_status') != 'not_requested':
        await edit_or_send_message(message, "❌ Анкета уже подана на верификацию или обработана.", reply_markup=current_menu)
        return
    
    await edit_or_send_message(
        message,
        "📸 **Верификация аккаунта**\n\n"
        "Для подтверждения того, что ты студент, отправь фотографию "
        "своего студенческого билета.\n\n"
        "**Требования к фото:**\n"
        "• Четкое изображение\n"
        "• Видны основные данные\n"
        "• Хорошее освещение\n\n"
        "Отправь фото:",
        reply_markup=current_menu
    )
    
    from handlers.states import VerificationStates
    await state.set_state(VerificationStates.student_card_photo)

# Админская панель теперь обрабатывается в handlers/admin_mode.py

@router.message(F.text == "🔍 Поиск людей")
async def search_people_menu(message: Message):
    """Поиск людей через меню"""
    user = await db.get_user(message.from_user.id)
    
    # Определяем текущее меню
    if not user:
        user_state = 'new'
        current_menu = get_main_menu_keyboard('new', is_admin(message), admin_mode=False)
    else:
        user_state = determine_user_state(user)
        current_menu = get_main_menu_keyboard(user_state, is_admin(message), admin_mode=False)
    
    if not user or user['verification_status'] != 'approved':
        await edit_or_send_message(message, "❌ Эта функция доступна только верифицированным пользователям.", reply_markup=current_menu)
        return
    
    # Проверяем участие в мероприятиях
    events_count = await db.get_user_events_count(user['id'])
    
    if events_count == 0:
        await edit_or_send_message(
            message,
            "❌ **Для поиска людей нужно участие в мероприятиях**\n\n"
            "Сначала запишись хотя бы на одно мероприятие:\n"
            "🎉 Используй кнопку **Мероприятия**\n\n"
            "Это поможет находить людей с общими интересами! 🤝",
            reply_markup=current_menu
        )
        return
    
    await edit_or_send_message(
        message,
        f"🔍 **Поиск людей**\n\n"
        f"👥 Ты участвуешь в {events_count} мероприятии(ях)\n\n"
        "Функция поиска анкет будет доступна в следующем обновлении!\n"
        "Скоро ты сможешь:\n"
        "• Просматривать анкеты других студентов\n"
        "• Ставить лайки и дизлайки\n"
        "• Находить людей с общими мероприятиями\n\n"
        "Следи за обновлениями! 🚀",
        reply_markup=current_menu
    )

@router.message(F.text == "🎉 Мероприятия")
async def events_menu(message: Message):
    """Мероприятия через меню"""
    # Используем функцию из events.py с правильным названием
    from handlers.events import get_events_list_keyboard
    
    user = await db.get_user(message.from_user.id)
    
    # Определяем текущее меню
    if not user:
        user_state = 'new'
        current_menu = get_main_menu_keyboard('new', is_admin(message), admin_mode=False)
        await edit_or_send_message(message, "❌ Сначала зарегистрируйся в боте!", reply_markup=current_menu)
        return
    else:
        user_state = determine_user_state(user)
        current_menu = get_main_menu_keyboard(user_state, is_admin(message), admin_mode=False)
    
    if user['verification_status'] != 'approved':
        await edit_or_send_message(message, "❌ Эта функция доступна только верифицированным пользователям.", reply_markup=current_menu)
        return
    
    events = await db.get_active_events()
    
    text = f"🎉 **Мероприятия ({len(events)})**\n\n"
    if events:
        text += "Выбери мероприятие для подробной информации:"
    else:
        text += "Мероприятий пока нет. Следи за обновлениями!"
    
    # Получаем клавиатуру с мероприятиями (та же что используется в events.py)
    keyboard = get_events_list_keyboard(events, user['id'])
    
    await edit_or_send_message(message, text, reply_markup=keyboard)

# Обработчик "📸 Повторная верификация" удален - функция больше не нужна
# Пользователи используют кнопку "✏️ Редактировать" для исправления анкеты и повторной подачи

@router.message(F.text == "ℹ️ Статус верификации")
async def status_menu(message: Message):
    """Проверка статуса верификации через меню"""
    user = await db.get_user(message.from_user.id)
    
    # Определяем текущее меню
    if not user:
        user_state = 'new'
        current_menu = get_main_menu_keyboard('new', is_admin(message), admin_mode=False)
        await edit_or_send_message(message, "❌ У тебя пока нет анкеты.", reply_markup=current_menu)
        return
    
    # Используем новую логику состояний
    user_state = determine_user_state(user)
    current_menu = get_main_menu_keyboard(user_state, is_admin(message), admin_mode=False)
    
    await edit_or_send_message(
        message,
        f"ℹ️ **Статус верификации**\n\n"
        f"Текущее состояние: {get_status_emoji(user_state)} {get_status_text(user_state)}\n\n"
        f"📅 Анкета создана: {user['created_at'][:10] if user['created_at'] else 'Неизвестно'}",
        reply_markup=current_menu
    )

@router.message(F.text == "ℹ️ О боте")
async def about_bot_menu(message: Message):
    """Информация о боте через меню"""
    # Используем новую функцию редактирования
    await edit_or_send_message(
        message,
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
    try:
        user_info = await message.bot.get_chat(actual_user_id)
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
