from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from handlers.states import RegistrationStates, VerificationStates
from database import Database
from config import PROFILE_LIMITS, DATABASE_URL
from utils import is_admin

router = Router()
db = Database(DATABASE_URL)

def get_course_keyboard():
    """Клавиатура для выбора курса"""
    keyboard = []
    for i in range(1, 6):
        keyboard.append([InlineKeyboardButton(text=f"{i} курс", callback_data=f"course_{i}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_preview_keyboard():
    """Клавиатура для превью анкеты"""
    keyboard = [
        [InlineKeyboardButton(text="💾 Сохранить", callback_data="save_profile")],
        [InlineKeyboardButton(text="✏️ Изменить", callback_data="edit_profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def format_profile(user_data: dict) -> str:
    """Форматирование анкеты для показа"""
    course_text = f"{user_data.get('course', 'Не указан')} курс"
    major = user_data.get('major', 'Не указано')
    age = user_data.get('age', 'Не указан')
    name = user_data.get('name', 'Не указано')
    description = user_data.get('description', 'Не указано')
    
    return f"""
👤 **Твоя анкета:**

📚 Курс: {course_text}
🎓 Направление: {major}
🎂 Возраст: {age}
✨ Имя: {name}

📝 О себе:
{description}
"""

@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    from handlers.menu import get_main_menu_keyboard
    from handlers.admin import is_in_admin_mode
    
    user = await db.get_user(message.from_user.id)
    is_user_admin = is_admin(message)
    admin_mode = is_in_admin_mode(message.from_user.id)
    
    # Определяем состояние пользователя
    from handlers.menu import determine_user_state
    user_state = determine_user_state(user)
    
    # Генерируем соответствующий ответ
    if user_state == 'approved':
        await message.answer(
            "🎉 **Добро пожаловать в UniMeetingBot!**\n\n"
            "Ты уже зарегистрирован и верифицирован!\n\n"
            "**Доступные функции:**\n"
            "• 👤 Просмотр и редактирование анкеты\n"
            "• 🔍 Поиск новых знакомств\n"
            "• 🎉 Участие в мероприятиях\n\n"
            "Используй меню ниже для навигации:",
            reply_markup=get_main_menu_keyboard(user_state, is_user_admin, admin_mode)
        )
        return
    
    elif user_state == 'draft':
        await message.answer(
            "📝 **Твоя анкета готова!**\n\n"
            "Анкета создана, но ещё не подана на верификацию.\n\n"
            "**Что можно делать:**\n"
            "• 👤 Просмотреть анкету\n"
            "• ✏️ Внести изменения\n"
            "• 📤 Подать на верификацию\n\n"
            "После верификации получишь полный доступ:",
            reply_markup=get_main_menu_keyboard(user_state, is_user_admin, admin_mode)
        )
        return
    
    elif user_state == 'pending':
        await message.answer(
            "⏳ **Анкета на модерации**\n\n"
            "Твоя анкета отправлена администраторам на проверку.\n"
            "Ожидай подтверждения!\n\n"
            "После одобрения получишь доступ ко всем функциям:",
            reply_markup=get_main_menu_keyboard(user_state, is_user_admin, admin_mode)
        )
        return
    
    elif user_state == 'rejected':
        await message.answer(
            "❌ **Заявка отклонена**\n\n"
            "К сожалению, твоя предыдущая заявка была отклонена.\n\n"
            "**Что можно сделать:**\n"
            "• ✏️ Изменить данные анкеты\n"
            "• 📸 Отправить новое фото студбилета\n\n"
            "Используй кнопки ниже:",
            reply_markup=get_main_menu_keyboard(user_state, is_user_admin, admin_mode)
        )
        return
    
    # Новый пользователь (user_state == 'new')
    # Начинаем создание анкеты сразу
    await message.answer(
        "🎓 **Привет! Добро пожаловать в UniMeetingBot!**\n\n"
        "Этот бот поможет тебе найти новых друзей среди студентов.\n"
        "Давай создадим твою анкету! 🚀\n\n"
        "Сначала выбери свой курс:",
        reply_markup=get_course_keyboard()
    )
    await state.set_state(RegistrationStates.course)
    
    # Создаем пользователя, если его нет
    if not user:
        await db.create_user(message.from_user.id)

@router.callback_query(F.data.startswith("course_"))
async def process_course(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора курса"""
    course = int(callback.data.split("_")[1])
    await state.update_data(course=course)
    
    await callback.message.edit_text(
        f"✅ Курс: {course}\n\n"
        "🎓 Теперь напиши свое направление обучения:"
    )
    await state.set_state(RegistrationStates.major)

@router.message(RegistrationStates.major)
async def process_major(message: Message, state: FSMContext):
    """Обработка ввода направления"""
    major = message.text.strip()
    
    if len(major) < PROFILE_LIMITS['major_min'] or len(major) > PROFILE_LIMITS['major_max']:
        await message.answer(f"❌ Направление должно содержать от {PROFILE_LIMITS['major_min']} до {PROFILE_LIMITS['major_max']} символов. Попробуй еще раз:")
        return
    
    await state.update_data(major=major)
    await message.answer(
        f"✅ Направление: {major}\n\n"
        "🎂 Теперь укажи свой возраст (от 16 до 30 лет):"
    )
    await state.set_state(RegistrationStates.age)

@router.message(RegistrationStates.age)
async def process_age(message: Message, state: FSMContext):
    """Обработка ввода возраста"""
    try:
        age = int(message.text.strip())
        if age < PROFILE_LIMITS['age_min'] or age > PROFILE_LIMITS['age_max']:
            await message.answer(f"❌ Возраст должен быть от {PROFILE_LIMITS['age_min']} до {PROFILE_LIMITS['age_max']} лет. Попробуй еще раз:")
            return
    except ValueError:
        await message.answer("❌ Пожалуйста, введи возраст числом:")
        return
    
    await state.update_data(age=age)
    await message.answer(
        f"✅ Возраст: {age}\n\n"
        "✨ Как тебя зовут?"
    )
    await state.set_state(RegistrationStates.name)

@router.message(RegistrationStates.name)
async def process_name(message: Message, state: FSMContext):
    """Обработка ввода имени"""
    name = message.text.strip()
    
    if len(name) < PROFILE_LIMITS['name_min'] or len(name) > PROFILE_LIMITS['name_max']:
        await message.answer(f"❌ Имя должно содержать от {PROFILE_LIMITS['name_min']} до {PROFILE_LIMITS['name_max']} символов. Попробуй еще раз:")
        return
    
    await state.update_data(name=name)
    await message.answer(
        f"✅ Имя: {name}\n\n"
        f"📝 Расскажи о себе! Опиши свои интересы, увлечения, что ищешь в общении "
        f"(до {PROFILE_LIMITS['description_max']} символов):"
    )
    await state.set_state(RegistrationStates.description)

@router.message(RegistrationStates.description)
async def process_description(message: Message, state: FSMContext):
    """Обработка ввода описания"""
    description = message.text.strip()
    
    if len(description) < PROFILE_LIMITS['description_min'] or len(description) > PROFILE_LIMITS['description_max']:
        await message.answer(f"❌ Описание должно содержать от {PROFILE_LIMITS['description_min']} до {PROFILE_LIMITS['description_max']} символов. Попробуй еще раз:")
        return
    
    await state.update_data(description=description)
    await message.answer(
        f"✅ Описание добавлено!\n\n"
        "📸 Отправь свою фотографию:"
    )
    await state.set_state(RegistrationStates.photo)

@router.message(RegistrationStates.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    """Обработка загрузки фотографии"""
    photo_file_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=photo_file_id)
    
    # Показываем превью анкеты
    user_data = await state.get_data()
    profile_text = format_profile(user_data)
    
    await message.answer_photo(
        photo=photo_file_id,
        caption=profile_text,
        reply_markup=get_preview_keyboard()
    )
    await state.set_state(RegistrationStates.preview)

@router.message(RegistrationStates.photo)
async def process_photo_invalid(message: Message, state: FSMContext):
    """Обработка некорректной загрузки фото"""
    await message.answer("❌ Пожалуйста, отправь фотографию:")

@router.callback_query(F.data == "save_profile")
async def save_profile(callback: CallbackQuery, state: FSMContext):
    """Сохранение анкеты"""
    user_data = await state.get_data()
    
    # Получаем текущий статус пользователя
    user = await db.get_user(callback.from_user.id)
    current_status = user['verification_status'] if user else 'not_requested'
    
    # Сохраняем данные в базу
    await db.update_user(
        telegram_id=callback.from_user.id,
        name=user_data['name'],
        age=user_data['age'],
        course=user_data['course'],
        major=user_data['major'],
        description=user_data['description'],
        photo_file_id=user_data['photo_file_id']
    )
    
    # Проверяем состояние пользователя для принятия решения о верификации
    from handlers.menu import determine_user_state
    user_updated = await db.get_user(callback.from_user.id)  # Получаем обновленные данные
    new_state = determine_user_state(user_updated)
    
    if current_status == 'approved':
        # Пользователь уже верифицирован - не запрашиваем повторную верификацию
        await callback.message.edit_caption(
            caption="✅ **Анкета обновлена!**\n\n"
            "Изменения сохранены. Повторная верификация не требуется.\n\n"
            "Можешь продолжать пользоваться всеми функциями бота!"
        )
        # Меню НЕ обновляем - оно остается таким же (approved)
        await state.clear()

    elif current_status == 'not_requested' and user and user.get('name') is None:
        # Это первое создание анкеты (new -> draft) - обновляем меню
        await callback.message.edit_caption(
            caption="✅ **Анкета сохранена!**\n\n"
            "Твоя анкета сохранена как черновик.\n\n"
            "**Что дальше:**\n"
            "• Можешь ещё раз просмотреть и отредактировать\n"
            "• Когда будешь готов - подай на верификацию\n\n"
            "Используй кнопки меню:"
        )

        # Обновляем меню только при первом создании (new -> draft)
        from handlers.menu import update_user_menu
        await update_user_menu(callback.message, new_state, callback.from_user.id)
        await state.clear()

    else:
        # Редактирование существующей анкеты - меню НЕ меняется
        await callback.message.edit_caption(
            caption="✅ **Анкета обновлена!**\n\n"
            "Изменения сохранены.\n\n"
            "Можешь продолжать пользоваться ботом!"
        )
        # Меню НЕ обновляем - оно остается таким же
        await state.clear()

@router.callback_query(F.data == "edit_profile")
async def edit_profile_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование анкеты"""
    await callback.message.edit_text(
        "✏️ Хорошо! Давай заново заполним анкету.\n\n"
        "Сначала выбери свой курс:",
        reply_markup=get_course_keyboard()
    )
    await state.set_state(RegistrationStates.course)

@router.message(VerificationStates.student_card_photo, F.photo)
async def process_verification_photo(message: Message, state: FSMContext):
    """Обработка фото для верификации"""
    from handlers.admin import notify_admins_about_verification
    from aiogram import Bot
    
    photo_file_id = message.photo[-1].file_id
    
    # Получаем пользователя
    user = await db.get_user(message.from_user.id)
    
    # Проверяем, не был ли пользователь уже верифицирован
    if user['verification_status'] == 'approved':
        await message.answer(
            "ℹ️ **Ты уже верифицирован!**\n\n"
            "Повторная верификация не требуется.\n"
            "Можешь пользоваться всеми функциями бота."
        )
        await state.clear()
        return
    
    # Создаем заявку на верификацию
    request_id = await db.create_verification_request(user['id'], photo_file_id)
    
    await message.answer(
        "✅ Фото отправлено на модерацию!\n\n"
        "⏳ Ожидай подтверждения от администраторов.\n"
        "Мы уведомим тебя, как только анкета будет проверена."
    )
    
    # Уведомляем админов
    bot = Bot.get_current()
    verification_data = {
        'name': user['name'],
        'course': user['course'],
        'major': user['major'],
        'id': request_id
    }
    await notify_admins_about_verification(bot, verification_data)
    
    await state.clear()

@router.message(VerificationStates.student_card_photo)
async def process_verification_photo_invalid(message: Message, state: FSMContext):
    """Обработка некорректной загрузки фото для верификации"""
    await message.answer("❌ Пожалуйста, отправь фотографию со студенческим билетом:")

@router.message(Command("profile"))
async def view_profile(message: Message):
    """Просмотр анкеты"""
    user = await db.get_user(message.from_user.id)
    
    if not user or not user['name']:
        await message.answer("❌ У тебя пока нет анкеты. Используй /start для создания.")
        return
    
    profile_text = format_profile(user)
    
    if user['photo_file_id']:
        await message.answer_photo(
            photo=user['photo_file_id'],
            caption=profile_text
        )
    else:
        await message.answer(profile_text)

def get_rejected_user_menu():
    """Меню для пользователей с отклоненной заявкой"""
    keyboard = [
        [InlineKeyboardButton(text="✏️ Изменить анкету", callback_data="edit_start")],
        [InlineKeyboardButton(text="📸 Отправить новое фото студбилета", callback_data="resend_verification")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("edit"))
async def edit_profile_command(message: Message, state: FSMContext = None):
    """Команда редактирования анкеты"""
    user = await db.get_user(message.from_user.id)
    
    if not user:
        await message.answer("❌ У тебя пока нет анкеты. Используй /start для создания.")
        return
    
    if user['verification_status'] == 'pending':
        await message.answer(
            "❌ Нельзя редактировать анкету во время модерации.\n"
            "Дождись результата проверки."
        )
        return
    
    if user['verification_status'] == 'rejected':
        await message.answer(
            "❌ Твоя заявка была отклонена.\n\n"
            "Выбери действие:",
            reply_markup=get_rejected_user_menu()
        )
        return
    
    # Если state не передан (вызов из меню), получаем его из контекста
    if state is None:
        from aiogram.fsm.context import FSMContext
        from aiogram import Bot
        bot = Bot.get_current()
        from aiogram.fsm.storage.base import StorageKey
        
        # Получаем storage из dispatcher
        try:
            dispatcher = bot.dispatcher if hasattr(bot, 'dispatcher') else None
            storage = dispatcher.storage if dispatcher else None
            
            if storage:
                key = StorageKey(bot.id, message.from_user.id, message.from_user.id)
                state = FSMContext(storage, key)
            else:
                await message.answer("❌ Техническая ошибка. Попробуй команду /edit")
                return
        except Exception as e:
            await message.answer("❌ Техническая ошибка. Попробуй команду /edit")
            return
    
    await message.answer(
        "✏️ Давай обновим твою анкету!\n\n"
        "Сначала выбери свой курс:",
        reply_markup=get_course_keyboard()
    )
    await state.set_state(RegistrationStates.course)

@router.callback_query(F.data == "edit_start")
async def edit_start_callback(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование анкеты (callback)"""
    await callback.message.edit_text(
        "✏️ Давай обновим твою анкету!\n\n"
        "Сначала выбери свой курс:",
        reply_markup=get_course_keyboard()
    )
    await state.set_state(RegistrationStates.course)

@router.callback_query(F.data == "resend_verification")
async def resend_verification_callback(callback: CallbackQuery, state: FSMContext):
    """Повторная отправка фото для верификации"""
    await callback.message.edit_text(
        "📸 Отправь новое фото со своим студенческим билетом:\n\n"
        "Убедись, что:\n"
        "• Фото четкое и разборчивое\n"
        "• Видны все данные студбилета\n"
        "• Данные соответствуют твоей анкете"
    )
    await state.set_state(VerificationStates.student_card_photo)
