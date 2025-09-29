from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    """Состояния для регистрации пользователя"""
    course = State()
    major = State()
    age = State()
    name = State()
    description = State()
    photo = State()
    preview = State()
    
class VerificationStates(StatesGroup):
    """Состояния для верификации"""
    student_card_photo = State()

class EventStates(StatesGroup):
    """Состояния для создания/редактирования мероприятий"""
    name = State()
    description = State()
    edit_name = State()
    edit_description = State()
