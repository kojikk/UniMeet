import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Database
DATABASE_URL = os.getenv('DATABASE_URL', 'database.db')

# Admin IDs и usernames (парсинг из .env как строка с запятыми)
def parse_admins() -> tuple[List[int], List[str]]:
    """Парсинг ID и username админов из переменной окружения"""
    admins_str = os.getenv('ADMIN_IDS', '')
    if not admins_str:
        return [], []
    
    admin_ids = []
    admin_usernames = []
    
    for admin_str in admins_str.split(','):
        admin_str = admin_str.strip()
        if not admin_str:
            continue
            
        # Если это число - значит ID
        try:
            admin_id = int(admin_str)
            admin_ids.append(admin_id)
        except ValueError:
            # Если не число - значит username (убираем @ если есть)
            username = admin_str.lstrip('@').lower()
            admin_usernames.append(username)
    
    return admin_ids, admin_usernames

ADMIN_IDS, ADMIN_USERNAMES = parse_admins()

# Debug mode
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Лимиты на поля анкеты
PROFILE_LIMITS = {
    'name_min': int(os.getenv('NAME_MIN_LENGTH', '2')),
    'name_max': int(os.getenv('NAME_MAX_LENGTH', '50')),
    'major_min': int(os.getenv('MAJOR_MIN_LENGTH', '2')),
    'major_max': int(os.getenv('MAJOR_MAX_LENGTH', '100')),
    'description_min': int(os.getenv('DESCRIPTION_MIN_LENGTH', '10')),
    'description_max': int(os.getenv('DESCRIPTION_MAX_LENGTH', '500')),
    'age_min': int(os.getenv('AGE_MIN', '16')),
    'age_max': int(os.getenv('AGE_MAX', '30')),
}
