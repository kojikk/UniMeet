from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
import logging

from database import Database
from config import DATABASE_URL, ADMIN_IDS, ADMIN_USERNAMES
from utils import is_admin, get_user_display_name

router = Router()
db = Database(DATABASE_URL)
logger = logging.getLogger(__name__)

def get_admin_main_keyboard():
    """Главная клавиатура админа"""
    keyboard = [
        [InlineKeyboardButton(text="📋 Заявки на верификацию", callback_data="admin_pending")],
        [InlineKeyboardButton(text="🎉 Управление мероприятиями", callback_data="admin_events_list")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_verification_keyboard(request_id: int):
    """Клавиатура для заявки на верификацию"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"verify_approve_{request_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"verify_reject_{request_id}")
        ],
        [InlineKeyboardButton(text="👤 Анкета", callback_data=f"verify_profile_{request_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_pending")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_profile_view_keyboard(request_id: int):
    """Клавиатура для просмотра анкеты"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"verify_approve_{request_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"verify_reject_{request_id}")
        ],
        [InlineKeyboardButton(text="🔙 Скрыть анкету", callback_data=f"verify_hide_profile_{request_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_pending")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_pending_list_keyboard(verifications):
    """Клавиатура со списком заявок"""
    keyboard = []
    for verification in verifications:
        text = f"{verification['name']} ({verification['course']} курс)"
        keyboard.append([InlineKeyboardButton(
            text=text,
            callback_data=f"verify_view_{verification['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_pending")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def format_profile_for_admin(verification):
    """Форматирование анкеты для админа"""
    return f"""
👤 **Анкета пользователя:**

📚 Курс: {verification['course']}
🎓 Направление: {verification['major']}
🎂 Возраст: {verification['age']}
✨ Имя: {verification['name']}

📝 О себе:
{verification['description']}

🆔 Telegram ID: {verification['telegram_id']}
📅 Заявка подана: {verification['created_at'][:16]}
"""

@router.message(Command("admin_panel"))
async def admin_panel_command(message: Message):
    """Главная админ панель"""
    if not is_admin(message):
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    pending_count = len(await db.get_pending_verifications())
    
    text = f"""
🔧 **Панель администратора**

📊 Статистика:
• Заявок на рассмотрении: {pending_count}

Выберите действие:
"""
    
    await message.answer(text, reply_markup=get_admin_main_keyboard())

@router.message(Command("pending"))
async def pending_command(message: Message):
    """Список заявок на верификацию"""
    if not is_admin(message):
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    verifications = await db.get_pending_verifications()
    
    if not verifications:
        await message.answer("✅ Нет заявок на рассмотрении!")
        return
    
    text = f"📋 **Заявки на верификацию ({len(verifications)})**\n\nВыберите заявку для рассмотрения:"
    await message.answer(text, reply_markup=get_pending_list_keyboard(verifications))

@router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery):
    """Главная админ панель (callback)"""
    if not is_admin(callback):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    pending_count = len(await db.get_pending_verifications())
    
    text = f"""
🔧 **Панель администратора**

📊 Статистика:
• Заявок на рассмотрении: {pending_count}

Выберите действие:
"""
    
    await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard())

@router.callback_query(F.data == "admin_pending")
async def admin_pending_callback(callback: CallbackQuery):
    """Список заявок (callback)"""
    if not is_admin(callback):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    verifications = await db.get_pending_verifications()
    
    if not verifications:
        await callback.message.edit_text("✅ Нет заявок на рассмотрении!")
        return
    
    text = f"📋 **Заявки на верификацию ({len(verifications)})**\n\nВыберите заявку для рассмотрения:"
    await callback.message.edit_text(text, reply_markup=get_pending_list_keyboard(verifications))

@router.callback_query(F.data.startswith("verify_view_"))
async def verify_view_callback(callback: CallbackQuery):
    """Просмотр конкретной заявки"""
    if not is_admin(callback):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    request_id = int(callback.data.split("_")[2])
    verification = await db.get_verification_by_id(request_id)
    
    if not verification:
        await callback.answer("❌ Заявка не найдена.", show_alert=True)
        return
    
    text = f"🔍 **Заявка на верификацию #{verification['id']}**"
    
    # Отправляем фото со студенческим билетом
    try:
        await callback.message.answer_photo(
            photo=verification['student_card_photo'],
            caption=text,
            reply_markup=get_verification_keyboard(request_id)
        )
    except Exception as e:
        # Если не удалось отправить фото, отправляем текст
        await callback.message.edit_text(
            text=f"{text}\n\n❌ Ошибка загрузки фото верификации",
            reply_markup=get_verification_keyboard(request_id)
        )

@router.callback_query(F.data.startswith("verify_profile_"))
async def verify_profile_callback(callback: CallbackQuery):
    """Просмотр анкеты пользователя"""
    if not is_admin(callback):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    request_id = int(callback.data.split("_")[2])
    verification = await db.get_verification_by_id(request_id)
    
    if not verification:
        await callback.answer("❌ Заявка не найдена.", show_alert=True)
        return
    
    profile_text = format_profile_for_admin(verification)
    
    # Заменяем только caption и клавиатуру, оставляя то же фото
    await callback.message.edit_caption(
        caption=profile_text,
        reply_markup=get_profile_view_keyboard(request_id)
    )

@router.callback_query(F.data.startswith("verify_hide_profile_"))
async def verify_hide_profile_callback(callback: CallbackQuery):
    """Скрыть анкету и вернуть фото верификации"""
    if not is_admin(callback):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    request_id = int(callback.data.split("_")[3])
    verification = await db.get_verification_by_id(request_id)
    
    if not verification:
        await callback.answer("❌ Заявка не найдена.", show_alert=True)
        return
    
    # Возвращаем подпись к фото верификации
    text = f"🔍 **Заявка на верификацию #{verification['id']}**"
    
    await callback.message.edit_caption(
        caption=text,
        reply_markup=get_verification_keyboard(request_id)
    )

@router.callback_query(F.data.startswith("verify_approve_"))
async def verify_approve_callback(callback: CallbackQuery, bot: Bot):
    """Одобрить заявку"""
    if not is_admin(callback):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    request_id = int(callback.data.split("_")[2])
    verification = await db.get_verification_by_id(request_id)
    
    if not verification or verification['status'] != 'pending':
        await callback.answer("❌ Заявка не найдена или уже обработана.", show_alert=True)
        return
    
    # Обрабатываем заявку
    await db.process_verification(request_id, 'approved', callback.from_user.id)
    
    # Уведомляем пользователя и обновляем меню
    try:
        from handlers.menu import get_main_menu_keyboard
        from utils import get_user_display_name
        
        # Проверяем, является ли пользователь админом
        user_telegram_id = verification['telegram_id']
        user_is_admin = user_telegram_id in ADMIN_IDS
        
        await bot.send_message(
            chat_id=user_telegram_id,
            text="✅ **Поздравляем! Твоя анкета одобрена!**\n\n"
                 "🎉 Теперь ты можешь пользоваться всеми функциями бота:\n"
                 "• 👤 Просматривать и редактировать анкету\n"
                 "• 🔍 Искать новых друзей (скоро)\n"
                 "• 🎉 Участвовать в мероприятиях (скоро)\n\n"
                 "Используй обновленное меню ниже!",
            reply_markup=get_main_menu_keyboard('approved', user_is_admin)
        )
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление пользователю {verification['telegram_id']}: {e}")
    
    admin_name = get_user_display_name(callback.from_user)
    await callback.message.edit_caption(
        caption=f"✅ **Заявка одобрена**\n\n"
                f"Администратор: {admin_name}\n"
                f"Пользователь уведомлен."
    )
    
    await callback.answer("✅ Заявка одобрена!", show_alert=False)
    
    logger.info(f"Admin {callback.from_user.id} approved verification request {request_id}")

@router.callback_query(F.data.startswith("verify_reject_"))
async def verify_reject_callback(callback: CallbackQuery, bot: Bot):
    """Отклонить заявку"""
    if not is_admin(callback):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    request_id = int(callback.data.split("_")[2])
    verification = await db.get_verification_by_id(request_id)
    
    if not verification or verification['status'] != 'pending':
        await callback.answer("❌ Заявка не найдена или уже обработана.", show_alert=True)
        return
    
    # Обрабатываем заявку
    await db.process_verification(request_id, 'rejected', callback.from_user.id)
    
    # Уведомляем пользователя и обновляем меню
    try:
        from handlers.menu import get_main_menu_keyboard
        
        # Проверяем, является ли пользователь админом
        user_telegram_id = verification['telegram_id']
        user_is_admin = user_telegram_id in ADMIN_IDS
        
        await bot.send_message(
            chat_id=user_telegram_id,
            text="❌ **К сожалению, твоя заявка отклонена**\n\n"
                 "**Возможные причины:**\n"
                 "• Фото студенческого билета неразборчиво\n"
                 "• Данные в анкете не соответствуют студбилету\n"
                 "• Нарушение правил сервиса\n\n"
                 "**Что можно сделать:**\n"
                 "• ✏️ Изменить анкету\n"
                 "• 📸 Отправить новое фото студбилета\n\n"
                 "Используй кнопки меню ниже:",
            reply_markup=get_main_menu_keyboard('rejected', user_is_admin)
        )
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление пользователю {verification['telegram_id']}: {e}")
    
    admin_name = get_user_display_name(callback.from_user)
    await callback.message.edit_caption(
        caption=f"❌ **Заявка отклонена**\n\n"
                f"Администратор: {admin_name}\n"
                f"Пользователь уведомлен."
    )
    
    await callback.answer("❌ Заявка отклонена!", show_alert=False)
    
    logger.info(f"Admin {callback.from_user.id} rejected verification request {request_id}")

@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery):
    """Статистика для админа"""
    if not is_admin(callback):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    # TODO: Добавить реальную статистику из БД
    await callback.answer("📊 Статистика будет добавлена в следующих версиях", show_alert=True)

@router.callback_query(F.data == "admin_close")
async def admin_close_callback(callback: CallbackQuery):
    """Закрыть админ панель"""
    if not is_admin(callback):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    await callback.message.edit_text("✅ Админ панель закрыта.")

async def notify_admins_about_verification(bot: Bot, verification_request):
    """Уведомить всех админов о новой заявке на верификацию"""
    admin_ids_to_notify = ADMIN_IDS.copy()
    
    # Получаем пользователей по username
    for username in ADMIN_USERNAMES:
        # TODO: В реальном проекте нужно кэшировать username -> id mapping
        pass
    
    message_text = f"""
🔔 **Новая заявка на верификацию!**

👤 Пользователь: {verification_request['name']}
📚 Курс: {verification_request['course']}
🎓 Направление: {verification_request['major']}

Для рассмотрения используйте:
/pending - список заявок
/admin_panel - админ панель
"""
    
    for admin_id in admin_ids_to_notify:
        try:
            await bot.send_message(admin_id, message_text)
        except Exception as e:
            logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
