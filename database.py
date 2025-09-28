import aiosqlite
import logging
from datetime import datetime
from typing import Optional, Dict, Any

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def init_db(self):
        """Инициализация базы данных и создание таблиц"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    name TEXT,
                    age INTEGER,
                    course INTEGER,
                    major TEXT,
                    description TEXT,
                    photo_file_id TEXT,
                    verification_status TEXT DEFAULT 'not_requested',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица заявок на верификацию
            await db.execute('''
                CREATE TABLE IF NOT EXISTS verification_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    student_card_photo TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            await db.commit()
            logging.info("База данных инициализирована")
    
    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получить пользователя по Telegram ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                'SELECT * FROM users WHERE telegram_id = ?',
                (telegram_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def create_user(self, telegram_id: int) -> int:
        """Создать нового пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'INSERT INTO users (telegram_id) VALUES (?)',
                (telegram_id,)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def update_user(self, telegram_id: int, **kwargs):
        """Обновить данные пользователя"""
        if not kwargs:
            return
        
        set_clause = ', '.join(f'{key} = ?' for key in kwargs.keys())
        values = list(kwargs.values()) + [telegram_id]
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f'UPDATE users SET {set_clause} WHERE telegram_id = ?',
                values
            )
            await db.commit()
    
    async def create_verification_request(self, user_id: int, student_card_photo: str) -> int:
        """Создать заявку на верификацию"""
        async with aiosqlite.connect(self.db_path) as db:
            # Сначала обновляем статус пользователя
            await db.execute(
                'UPDATE users SET verification_status = ? WHERE id = ?',
                ('pending', user_id)
            )
            
            # Создаем заявку на верификацию
            cursor = await db.execute(
                'INSERT INTO verification_requests (user_id, student_card_photo) VALUES (?, ?)',
                (user_id, student_card_photo)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить пользователя по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                'SELECT * FROM users WHERE id = ?',
                (user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
