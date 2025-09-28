#!/usr/bin/env python3
"""
Скрипт для настройки администраторов бота
Запускайте этот скрипт для добавления/удаления админов
"""

import asyncio
from database import Database
from config import DATABASE_URL

async def main():
    db = Database(DATABASE_URL)
    await db.init_db()
    
    print("🔧 Настройка администраторов UniMeetingBot")
    print("=" * 50)
    
    while True:
        print("\nВыберите действие:")
        print("1. Добавить администратора")
        print("2. Показать всех админов") 
        print("3. Выйти")
        
        choice = input("\nВвод (1-3): ").strip()
        
        if choice == "1":
            print("\nДобавление администратора:")
            admin_input = input("Введите Telegram ID или username: ").strip()
            
            # Проверяем, это ID или username
            try:
                admin_id = int(admin_input)
                await db.add_admin(admin_id, is_super_admin=True)
                print(f"✅ Администратор {admin_id} добавлен!")
            except ValueError:
                print("❌ Пока поддерживаются только Telegram ID")
                print("Используйте @userinfobot для получения ID")
        
        elif choice == "2":
            print("\n📋 Список администраторов:")
            # TODO: добавить метод получения всех админов из БД
            print("Функция будет добавлена в следующей версии")
        
        elif choice == "3":
            print("👋 До свидания!")
            break
        
        else:
            print("❌ Неверный выбор. Попробуйте снова.")

if __name__ == "__main__":
    asyncio.run(main())
