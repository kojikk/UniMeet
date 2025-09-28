import aiosqlite
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

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
                    admin_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (admin_id) REFERENCES admins (telegram_id)
                )
            ''')
            
            # Таблица админов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    telegram_id INTEGER PRIMARY KEY,
                    is_super_admin BOOLEAN DEFAULT FALSE,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    async def get_pending_verifications(self) -> List[Dict[str, Any]]:
        """Получить все заявки на верификацию со статусом pending"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT vr.*, u.name, u.age, u.course, u.major, u.description, u.photo_file_id, u.telegram_id
                FROM verification_requests vr
                JOIN users u ON vr.user_id = u.id
                WHERE vr.status = 'pending'
                ORDER BY vr.created_at ASC
            ''')
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_verification_by_id(self, request_id: int) -> Optional[Dict[str, Any]]:
        """Получить заявку на верификацию по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT vr.*, u.name, u.age, u.course, u.major, u.description, u.photo_file_id, u.telegram_id
                FROM verification_requests vr
                JOIN users u ON vr.user_id = u.id
                WHERE vr.id = ?
            ''', (request_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def process_verification(self, request_id: int, status: str, admin_id: int):
        """Обработать заявку на верификацию"""
        async with aiosqlite.connect(self.db_path) as db:
            # Обновляем заявку на верификацию
            await db.execute('''
                UPDATE verification_requests 
                SET status = ?, admin_id = ?, processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, admin_id, request_id))
            
            # Получаем user_id для обновления статуса пользователя
            cursor = await db.execute(
                'SELECT user_id FROM verification_requests WHERE id = ?',
                (request_id,)
            )
            row = await cursor.fetchone()
            if row:
                user_id = row[0]
                # Обновляем статус пользователя
                await db.execute(
                    'UPDATE users SET verification_status = ? WHERE id = ?',
                    (status, user_id)
                )
            
            await db.commit()
    
    async def add_admin(self, telegram_id: int, is_super_admin: bool = False):
        """Добавить админа"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT OR REPLACE INTO admins (telegram_id, is_super_admin) VALUES (?, ?)',
                (telegram_id, is_super_admin)
            )
            await db.commit()
    
    async def is_admin(self, telegram_id: int) -> bool:
        """Проверить, является ли пользователь админом"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT 1 FROM admins WHERE telegram_id = ?',
                (telegram_id,)
            )
            row = await cursor.fetchone()
            return row is not None
