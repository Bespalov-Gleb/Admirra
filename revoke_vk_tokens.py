#!/usr/bin/env python3
"""
Скрипт для отзыва всех токенов VK Ads для конкретного пользователя.

Согласно официальной документации VK Ads API:
POST /api/v2/oauth2/token/delete.json
Параметры: client_id, client_secret, username или user_id

Использование:
    python revoke_vk_tokens.py sintez.digital@mail.ru
    или
    python revoke_vk_tokens.py --user-id 12345678
    или
    python revoke_vk_tokens.py --username sintez.digital
"""

import os
import sys
import asyncio
import httpx
import logging
from typing import Optional, List
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

# VK Ads Credentials
VK_CLIENT_ID = os.getenv("VK_CLIENT_ID", "MZzDprGbNsWFXiUf")
VK_CLIENT_SECRET = os.getenv("VK_CLIENT_SECRET", "IrMSpXAmwarxeL3ElBaKeJa4tJAcfplfs1wOFQY81wAkTm2SmZ5M7QqVOvEyRgizdhWEM8HvzRNIFhb8fKppwjLZd2Y6DXxUhqDMkiCZ5tSUsMui3Cu5K6dgAAGWQGDmZTPtNMcCuxY54snEKQBEVOI6MC3LAzOpeY5pgUdNtEgfAuh9NgezVurPWHowo7mSUXydDOIFl73LsGmy4lXD1UNotp6szljPePjsy8O2hkX")

# Добавляем путь к корню проекта для импорта модулей
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core.database import SessionLocal
from core import models


async def revoke_vk_tokens_by_user_id(user_id: str) -> bool:
    """
    Отзывает все токены VK Ads для указанного user_id.
    
    Согласно официальной документации VK Ads API:
    POST /api/v2/oauth2/token/delete.json
    Параметры: client_id, client_secret, user_id
    
    Args:
        user_id: VK Ads user_id пользователя
        
    Returns:
        bool: True если токены успешно отозваны, False при ошибке
    """
    if not VK_CLIENT_ID or not VK_CLIENT_SECRET:
        logger.error("❌ VK_CLIENT_ID и VK_CLIENT_SECRET должны быть установлены в .env")
        return False
    
    logger.info(f"🔄 Отзыв всех токенов VK Ads для user_id: {user_id}")
    logger.info(f"   Client ID: {VK_CLIENT_ID}")
    
    try:
        async with httpx.AsyncClient() as client:
            revoke_url = "https://ads.vk.com/api/v2/oauth2/token/delete.json"
            
            payload = {
                "client_id": VK_CLIENT_ID,
                "client_secret": VK_CLIENT_SECRET,
                "user_id": user_id
            }
            
            logger.info(f"📡 Отправка запроса на отзыв токенов...")
            logger.info(f"   URL: {revoke_url}")
            logger.info(f"   Payload: client_id={VK_CLIENT_ID}, user_id={user_id}")
            
            response = await client.post(revoke_url, data=payload, timeout=30.0)
            
            logger.info(f"📡 Ответ VK Ads API: {response.status_code}")
            
            # 200 означает успешный отзыв
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    logger.info(f"✅ Все токены VK Ads успешно отозваны для user_id: {user_id}")
                    logger.info(f"   Ответ API: {response_data}")
                    return True
                except:
                    logger.info(f"✅ Все токены VK Ads успешно отозваны для user_id: {user_id}")
                    return True
            
            # 400 может означать, что токены уже недействительны или не найдены
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error_description') or error_data.get('error', '')
                    logger.warning(f"⚠️ VK Ads API вернул 400: {error_msg}")
                    if 'invalid' in error_msg.lower() or 'not found' in error_msg.lower() or 'expired' in error_msg.lower():
                        logger.info(f"ℹ️ Токены уже недействительны или не найдены - цель достигнута")
                        return True
                except:
                    pass
                logger.error(f"❌ Ошибка отзыва токенов: {response.text[:200]}")
                return False
            
            # 401 означает ошибку авторизации (неверный client_id/client_secret)
            if response.status_code == 401:
                logger.error(f"❌ Ошибка авторизации: Неверный client_id или client_secret (401)")
                return False
            
            # Другие ошибки
            logger.error(f"❌ Ошибка отзыва токенов: {response.status_code} - {response.text[:200]}")
            return False
            
    except httpx.RequestError as req_err:
        logger.error(f"❌ Ошибка сети при отзыве токенов: {req_err}")
        return False
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка при отзыве токенов: {e}")
        import traceback
        traceback.print_exc()
        return False


async def revoke_vk_tokens_by_username(username: str) -> bool:
    """
    Отзывает все токены VK Ads для указанного username (логина).
    
    Согласно официальной документации VK Ads API:
    POST /api/v2/oauth2/token/delete.json
    Параметры: client_id, client_secret, username
    
    Args:
        username: Логин пользователя VK Ads
        
    Returns:
        bool: True если токены успешно отозваны, False при ошибке
    """
    if not VK_CLIENT_ID or not VK_CLIENT_SECRET:
        logger.error("❌ VK_CLIENT_ID и VK_CLIENT_SECRET должны быть установлены в .env")
        return False
    
    logger.info(f"🔄 Отзыв всех токенов VK Ads для username: {username}")
    logger.info(f"   Client ID: {VK_CLIENT_ID}")
    
    try:
        async with httpx.AsyncClient() as client:
            revoke_url = "https://ads.vk.com/api/v2/oauth2/token/delete.json"
            
            payload = {
                "client_id": VK_CLIENT_ID,
                "client_secret": VK_CLIENT_SECRET,
                "username": username
            }
            
            logger.info(f"📡 Отправка запроса на отзыв токенов...")
            logger.info(f"   URL: {revoke_url}")
            logger.info(f"   Payload: client_id={VK_CLIENT_ID}, username={username}")
            
            response = await client.post(revoke_url, data=payload, timeout=30.0)
            
            logger.info(f"📡 Ответ VK Ads API: {response.status_code}")
            
            # 200 означает успешный отзыв
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    logger.info(f"✅ Все токены VK Ads успешно отозваны для username: {username}")
                    logger.info(f"   Ответ API: {response_data}")
                    return True
                except:
                    logger.info(f"✅ Все токены VK Ads успешно отозваны для username: {username}")
                    return True
            
            # 400 может означать, что токены уже недействительны или не найдены
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error_description') or error_data.get('error', '')
                    logger.warning(f"⚠️ VK Ads API вернул 400: {error_msg}")
                    if 'invalid' in error_msg.lower() or 'not found' in error_msg.lower() or 'expired' in error_msg.lower():
                        logger.info(f"ℹ️ Токены уже недействительны или не найдены - цель достигнута")
                        return True
                except:
                    pass
                logger.error(f"❌ Ошибка отзыва токенов: {response.text[:200]}")
                return False
            
            # 401 означает ошибку авторизации (неверный client_id/client_secret)
            if response.status_code == 401:
                logger.error(f"❌ Ошибка авторизации: Неверный client_id или client_secret (401)")
                return False
            
            # Другие ошибки
            logger.error(f"❌ Ошибка отзыва токенов: {response.status_code} - {response.text[:200]}")
            return False
            
    except httpx.RequestError as req_err:
        logger.error(f"❌ Ошибка сети при отзыве токенов: {req_err}")
        return False
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка при отзыве токенов: {e}")
        import traceback
        traceback.print_exc()
        return False


def find_vk_user_ids_by_email(email: str) -> List[str]:
    """
    Находит все уникальные vk_user_id для пользователя по email.
    
    Args:
        email: Email пользователя
        
    Returns:
        List[str]: Список уникальных vk_user_id
    """
    db = SessionLocal()
    try:
        # Находим пользователя по email
        user = db.query(models.User).filter(models.User.email == email).first()
        
        if not user:
            logger.error(f"❌ Пользователь с email {email} не найден в базе данных")
            return []
        
        logger.info(f"✅ Найден пользователь: {user.email} (ID: {user.id})")
        
        # Находим все интеграции VK Ads для этого пользователя
        integrations = db.query(models.Integration).join(
            models.Client
        ).filter(
            models.Client.owner_id == user.id,
            models.Integration.platform == models.IntegrationPlatform.VK_ADS
        ).all()
        
        if not integrations:
            logger.warning(f"⚠️ Интеграции VK Ads не найдены для пользователя {email}")
            return []
        
        logger.info(f"📋 Найдено {len(integrations)} интеграций VK Ads")
        
        # Собираем уникальные vk_user_id
        user_ids = set()
        for integration in integrations:
            if integration.vk_user_id:
                user_ids.add(str(integration.vk_user_id))
                logger.info(f"   Интеграция {integration.id}: vk_user_id={integration.vk_user_id}")
            else:
                logger.warning(f"   Интеграция {integration.id}: vk_user_id не установлен")
        
        if not user_ids:
            logger.warning(f"⚠️ Не найдено ни одного vk_user_id для пользователя {email}")
            logger.info(f"   Попробуйте использовать --username или --user-id напрямую")
            return []
        
        logger.info(f"✅ Найдено {len(user_ids)} уникальных vk_user_id: {list(user_ids)}")
        return list(user_ids)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при поиске vk_user_id: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        db.close()


async def main():
    """Основная функция скрипта."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Отзыв всех токенов VK Ads для пользователя",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Отозвать токены по email (найдет vk_user_id в БД)
  python revoke_vk_tokens.py sintez.digital@mail.ru
  
  # Отозвать токены по user_id напрямую
  python revoke_vk_tokens.py --user-id 12345678
  
  # Отозвать токены по username напрямую
  python revoke_vk_tokens.py --username sintez.digital
        """
    )
    
    parser.add_argument(
        "email",
        nargs="?",
        help="Email пользователя (для поиска vk_user_id в БД)"
    )
    parser.add_argument(
        "--user-id",
        help="VK Ads user_id для отзыва токенов (используется напрямую, без поиска в БД)"
    )
    parser.add_argument(
        "--username",
        help="Логин пользователя VK Ads для отзыва токенов (используется напрямую, без поиска в БД)"
    )
    
    args = parser.parse_args()
    
    # Проверяем аргументы
    if not args.email and not args.user_id and not args.username:
        parser.error("Необходимо указать email, --user-id или --username")
    
    logger.info("=" * 60)
    logger.info("🔄 Отзыв токенов VK Ads")
    logger.info("=" * 60)
    logger.info("")
    
    success_count = 0
    total_count = 0
    
    # Если указан user_id напрямую
    if args.user_id:
        logger.info(f"📌 Использование user_id напрямую: {args.user_id}")
        total_count = 1
        if await revoke_vk_tokens_by_user_id(args.user_id):
            success_count = 1
    
    # Если указан username напрямую
    elif args.username:
        logger.info(f"📌 Использование username напрямую: {args.username}")
        total_count = 1
        if await revoke_vk_tokens_by_username(args.username):
            success_count = 1
    
    # Если указан email - ищем vk_user_id в БД
    else:
        logger.info(f"📌 Поиск vk_user_id для email: {args.email}")
        user_ids = find_vk_user_ids_by_email(args.email)
        
        if not user_ids:
            logger.error("❌ Не удалось найти vk_user_id для отзыва токенов")
            logger.info("   Попробуйте использовать --user-id или --username напрямую")
            sys.exit(1)
        
        total_count = len(user_ids)
        
        # Отзываем токены для каждого найденного user_id
        for user_id in user_ids:
            logger.info("")
            logger.info(f"🔄 Отзыв токенов для user_id: {user_id}")
            if await revoke_vk_tokens_by_user_id(user_id):
                success_count += 1
    
    # Итоги
    logger.info("")
    logger.info("=" * 60)
    if success_count == total_count:
        logger.info(f"✅ Успешно отозвано токенов: {success_count}/{total_count}")
    else:
        logger.warning(f"⚠️ Отозвано токенов: {success_count}/{total_count}")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

