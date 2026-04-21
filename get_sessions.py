#!/usr/bin/env python3
"""
Скрипт для получения .session файлов для магазина аккаунтов
Создает авторизованные session файлы через Telethon
"""

import asyncio
import os
from telethon import TelegramClient
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

API_ID = int(os.getenv("API_ID", input("Введите API_ID: ")))
API_HASH = os.getenv("API_HASH", input("Введите API_HASH: "))

def ensure_sessions_dir():
    """Создать папку sessions если её нет"""
    if not os.path.exists("sessions"):
        os.makedirs("sessions")
        print("📁 Создана папка 'sessions'")

async def get_single_session():
    """Получить один session файл"""
    print("\n" + "="*50)
    print("📱 ПОЛУЧЕНИЕ SESSION ФАЙЛА")
    print("="*50 + "\n")
    
    phone = input("Введите номер телефона (например +79991234567): ").strip()
    
    if not phone.startswith("+"):
        phone = "+" + phone
    
    session_name = f"sessions/{phone.replace('+', '')}"
    
    print(f"\n⏳ Подключение к аккаунту {phone}...")
    
    try:
        client = TelegramClient(session_name, API_ID, API_HASH)
        
        # Подключаемся
        await client.start(phone=phone)
        
        # Получаем информацию об аккаунте
        me = await client.get_me()
        
        print(f"\n✅ УСПЕШНО АВТОРИЗОВАН!")
        print(f"   Имя: {me.first_name} {me.last_name or ''}")
        print(f"   Номер: {me.phone}")
        print(f"   ID: {me.id}")
        print(f"   Username: @{me.username or 'Нет'}")
        
        # Отключаемся
        await client.disconnect()
        
        print(f"\n✅ Session файл сохранен: {session_name}.session")
        print(f"📁 Место: ./sessions/")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        return False

async def get_batch_sessions():
    """Получить несколько session файлов"""
    print("\n" + "="*50)
    print("📱 ПОЛУЧЕНИЕ НЕСКОЛЬКИХ SESSION ФАЙЛОВ")
    print("="*50 + "\n")
    
    count = int(input("Сколько аккаунтов будет добавлено? "))
    phones = []
    
    for i in range(count):
        phone = input(f"Номер телефона {i+1}: ").strip()
        if not phone.startswith("+"):
            phone = "+" + phone
        phones.append(phone)
    
    successful = 0
    failed = 0
    
    for phone in phones:
        print(f"\n⏳ Обработка {phone}...")
        
        session_name = f"sessions/{phone.replace('+', '')}"
        
        try:
            client = TelegramClient(session_name, API_ID, API_HASH)
            await client.start(phone=phone)
            
            me = await client.get_me()
            print(f"✅ {me.first_name} (ID: {me.id})")
            
            await client.disconnect()
            successful += 1
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            failed += 1
        
        # Небольшая задержка между авторизациями
        await asyncio.sleep(2)
    
    print(f"\n" + "="*50)
    print(f"✅ Успешно: {successful}")
    print(f"❌ Ошибок: {failed}")
    print("="*50)

async def check_sessions():
    """Проверить существующие session файлы"""
    print("\n" + "="*50)
    print("🔍 ПРОВЕРКА SESSION ФАЙЛОВ")
    print("="*50 + "\n")
    
    if not os.path.exists("sessions"):
        print("❌ Папка 'sessions' не найдена!")
        return
    
    sessions = [f for f in os.listdir("sessions") if f.endswith(".session")]
    
    if not sessions:
        print("❌ Session файлов не найдено!")
        return
    
    print(f"Найдено session файлов: {len(sessions)}\n")
    
    for session_file in sessions:
        session_path = f"sessions/{session_file}"
        
        try:
            client = TelegramClient(session_path, API_ID, API_HASH)
            await client.connect()
            
            is_auth = await client.is_user_authorized()
            
            if is_auth:
                me = await client.get_me()
                print(f"✅ {session_file}")
                print(f"   Имя: {me.first_name} {me.last_name or ''}")
                print(f"   Номер: {me.phone}")
                print(f"   ID: {me.id}\n")
            else:
                print(f"❌ {session_file} - НЕ АВТОРИЗОВАН\n")
            
            await client.disconnect()
            
        except Exception as e:
            print(f"❌ {session_file} - ОШИБКА: {e}\n")
        
        await asyncio.sleep(1)

async def delete_session():
    """Удалить session файл"""
    print("\n" + "="*50)
    print("🗑️  УДАЛЕНИЕ SESSION ФАЙЛА")
    print("="*50 + "\n")
    
    if not os.path.exists("sessions"):
        print("❌ Папка 'sessions' не найдена!")
        return
    
    sessions = [f for f in os.listdir("sessions") if f.endswith(".session")]
    
    if not sessions:
        print("❌ Session файлов не найдено!")
        return
    
    print("Доступные session файлы:")
    for i, session_file in enumerate(sessions, 1):
        print(f"{i}. {session_file}")
    
    try:
        choice = int(input("\nВыберите номер (или 0 для отмены): "))
        
        if choice == 0:
            print("Отмена")
            return
        
        if 1 <= choice <= len(sessions):
            session_file = sessions[choice - 1]
            os.remove(f"sessions/{session_file}")
            print(f"✅ Удален: {session_file}")
        else:
            print("❌ Неверный выбор")
    
    except ValueError:
        print("❌ Ошибка ввода")

async def main_menu():
    """Главное меню"""
    ensure_sessions_dir()
    
    while True:
        print("\n" + "="*50)
        print("🤖 МЕНЕДЖЕР SESSION ФАЙЛОВ")
        print("="*50)
        print("\n1️⃣  Получить один session файл")
        print("2️⃣  Получить несколько session файлов")
        print("3️⃣  Проверить существующие session файлы")
        print("4️⃣  Удалить session файл")
        print("5️⃣  Выход\n")
        
        choice = input("Выберите действие (1-5): ").strip()
        
        if choice == "1":
            await get_single_session()
        elif choice == "2":
            await get_batch_sessions()
        elif choice == "3":
            await check_sessions()
        elif choice == "4":
            await delete_session()
        elif choice == "5":
            print("\n👋 До встречи!")
            break
        else:
            print("❌ Неверный выбор, попробуйте снова")

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════╗
    ║   Minon Shop - Session Manager         ║
    ║   Менеджер session файлов              ║
    ╚════════════════════════════════════════╝
    """)
    
    try:
        asyncio.run(main_menu())
    except KeyboardInterrupt:
        print("\n\n👋 Программа прервана пользователем")
