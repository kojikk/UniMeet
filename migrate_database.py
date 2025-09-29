#!/usr/bin/env python3
"""
Скрипт для миграции базы данных
Добавляет новые поля в существующую базу данных
"""

import asyncio
import aiosqlite
import os
from config import DATABASE_URL

async def migrate_database():
    """Применить миграции к базе данных"""
    print("🔄 Начинаю миграцию базы данных...")
    
    async with aiosqlite.connect(DATABASE_URL) as db:
        try:
            # Проверяем, нужно ли добавить поле admin_id в verification_requests
            cursor = await db.execute("PRAGMA table_info(verification_requests)")
            columns = await cursor.fetchall()
            column_names = [column[1] for column in columns]
            
            if 'admin_id' not in column_names:
                print("➕ Добавляю поле admin_id в verification_requests...")
                await db.execute("ALTER TABLE verification_requests ADD COLUMN admin_id INTEGER")
                
            if 'processed_at' not in column_names:
                print("➕ Добавляю поле processed_at в verification_requests...")
                await db.execute("ALTER TABLE verification_requests ADD COLUMN processed_at TIMESTAMP")
            
            # Проверяем, существует ли таблица admins
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admins'")
            table_exists = await cursor.fetchone()
            
            if not table_exists:
                print("➕ Создаю таблицу admins...")
                await db.execute('''
                    CREATE TABLE admins (
                        telegram_id INTEGER PRIMARY KEY,
                        is_super_admin BOOLEAN DEFAULT FALSE,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            
            # Проверяем, существует ли таблица events
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
            events_table_exists = await cursor.fetchone()
            
            if not events_table_exists:
                print("➕ Создаю таблицу events...")
                await db.execute('''
                    CREATE TABLE events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_by INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (created_by) REFERENCES admins (telegram_id)
                    )
                ''')
            
            # Проверяем, существует ли таблица user_events
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_events'")
            user_events_table_exists = await cursor.fetchone()
            
            if not user_events_table_exists:
                print("➕ Создаю таблицу user_events...")
                await db.execute('''
                    CREATE TABLE user_events (
                        user_id INTEGER NOT NULL,
                        event_id INTEGER NOT NULL,
                        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, event_id),
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
                    )
                ''')
            
            await db.commit()
            print("✅ Миграция завершена успешно!")
            
        except Exception as e:
            print(f"❌ Ошибка миграции: {e}")
            await db.rollback()

async def reset_database():
    """Полностью пересоздать базу данных"""
    print("🔄 Пересоздание базы данных...")
    
    if os.path.exists(DATABASE_URL):
        os.remove(DATABASE_URL)
        print("🗑️ Старая база данных удалена")
    
    # Импортируем и инициализируем новую базу
    from database import Database
    db = Database(DATABASE_URL)
    await db.init_db()
    
    print("✅ Новая база данных создана!")

async def main():
    print("🛠️ Утилита миграции UniMeetingBot")
    print("=" * 40)
    
    while True:
        print("\nВыберите действие:")
        print("1. Мигрировать существующую базу данных")
        print("2. Полностью пересоздать базу данных (⚠️ потеря данных)")
        print("3. Выйти")
        
        choice = input("\nВвод (1-3): ").strip()
        
        if choice == "1":
            await migrate_database()
            break
        elif choice == "2":
            confirm = input("⚠️ Все данные будут потеряны. Продолжить? (yes/no): ").strip().lower()
            if confirm == "yes":
                await reset_database()
                break
            else:
                print("❌ Операция отменена")
        elif choice == "3":
            print("👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор")

if __name__ == "__main__":
    asyncio.run(main())
