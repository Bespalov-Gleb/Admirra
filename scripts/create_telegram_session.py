#!/usr/bin/env python3
"""
Один раз создаёт файл сессии для проверки номеров в Telegram.

Запуск:
  python -m scripts.create_telegram_session

Требует в .env или переменных окружения:
  TELEGRAM_CHECKER_API_ID
  TELEGRAM_CHECKER_API_HASH

После выполнения будет создан файл telegram_checker_session.session.
Укажите в .env: TELEGRAM_CHECKER_SESSION=telegram_checker_session
"""

import asyncio
import os
import sys

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

api_id = os.getenv("TELEGRAM_CHECKER_API_ID")
api_hash = os.getenv("TELEGRAM_CHECKER_API_HASH")

if not api_id or not api_hash:
    print("Укажите TELEGRAM_CHECKER_API_ID и TELEGRAM_CHECKER_API_HASH в .env")
    print("Получите на https://my.telegram.org → API development tools")
    sys.exit(1)

async def main():
    from telethon import TelegramClient

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    session_path = os.path.join(base_dir, "telegram_checker_session")
    print("Подключение к Telegram...")
    client = TelegramClient(session_path, int(api_id), api_hash)
    await client.start(phone=lambda: input("Введите ваш номер (для входа): "))
    session_file = session_path + ".session" if not session_path.endswith(".session") else session_path
    print(f"Сессия создана: {session_file}")
    print("Добавьте в .env: TELEGRAM_CHECKER_SESSION=" + os.path.join(base_dir, "telegram_checker_session"))
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
