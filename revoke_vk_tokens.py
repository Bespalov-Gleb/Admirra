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

    --force-all — только токены «аккаунта приложения» в VK, не всех рекламодателей.
    Чтобы освободить лимит у конкретного пользователя VK Ads (как в ошибке token_limit_exceeded):
    python revoke_vk_tokens.py --user-id 28468142
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
VK_CLIENT_ID = (os.getenv("VK_CLIENT_ID") or "").strip()
VK_CLIENT_SECRET = (os.getenv("VK_CLIENT_SECRET") or "").strip()

# Добавляем путь к корню проекта для импорта модулей
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core.database import SessionLocal
from core import models, security


async def revoke_vk_tokens_without_user_id() -> bool:
    """
    Отзывает все токены VK Ads без указания user_id.
    
    Согласно документации VK Ads API:
    "Если параметр username/user_id не передан, то будут удалены токены аккаунта,
    для которого был выдан доступ к API."
    
    Это удалит токены только для аккаунта приложения, а не для всех пользователей.
    
    Returns:
        bool: True если токены успешно отозваны, False при ошибке
    """
    if not VK_CLIENT_ID or not VK_CLIENT_SECRET:
        logger.error("❌ VK_CLIENT_ID и VK_CLIENT_SECRET должны быть установлены в .env")
        return False
    
    logger.info(f"🔄 Отзыв всех токенов VK Ads для аккаунта приложения (без user_id)")
    logger.info(f"   Client ID: {VK_CLIENT_ID}")
    logger.warning("   ⚠️ ВНИМАНИЕ: Это отзовет токены только для аккаунта приложения, не для всех пользователей!")
    
    try:
        async with httpx.AsyncClient() as client:
            revoke_url = "https://ads.vk.com/api/v2/oauth2/token/delete.json"
            
            payload = {
                "client_id": VK_CLIENT_ID,
                "client_secret": VK_CLIENT_SECRET
                # user_id не передаем - удалятся токены для аккаунта приложения
            }
            
            logger.info(f"📡 Отправка запроса на отзыв токенов...")
            logger.info(f"   URL: {revoke_url}")
            logger.info(f"   Payload: client_id={VK_CLIENT_ID} (без user_id)")
            logger.info(f"   Content-Type: application/x-www-form-urlencoded")
            
            # CRITICAL: Используем data= для application/x-www-form-urlencoded, не json=
            response = await client.post(
                revoke_url,
                data=payload,  # data= для form-urlencoded
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0
            )
            
            logger.info(f"📡 Ответ VK Ads API: {response.status_code}")
            
            # 200 или 204 означает успешный отзыв (204 = No Content - успешное выполнение без тела ответа)
            if response.status_code in [200, 204]:
                try:
                    response_data = response.json()
                    logger.info(f"✅ Все токены VK Ads успешно отозваны для аккаунта приложения")
                    logger.info(f"   Ответ API: {response_data}")
                    return True
                except:
                    logger.info(f"✅ Все токены VK Ads успешно отозваны для аккаунта приложения (статус {response.status_code})")
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


async def revoke_vk_tokens_by_user_id(user_id: str) -> bool:
    """
    Отзывает все токены VK Ads для указанного user_id.
    
    Согласно официальной документации VK Ads API:
    POST /api/v2/oauth2/token/delete.json
    Параметры: client_id, client_secret, username или user_id
    
    Args:
        user_id: VK Ads user_id пользователя (будет передан как username, если это логин)
        
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
            
            # Числовой id (как в callback ?user_id=) — сразу в поле user_id; иначе логин → username.
            looks_numeric = user_id.isdigit()
            if looks_numeric:
                payload = {
                    "client_id": VK_CLIENT_ID,
                    "client_secret": VK_CLIENT_SECRET,
                    "user_id": user_id,
                }
                log_field = f"user_id={user_id}"
            else:
                payload = {
                    "client_id": VK_CLIENT_ID,
                    "client_secret": VK_CLIENT_SECRET,
                    "username": user_id,
                }
                log_field = f"username={user_id}"
            
            logger.info(f"📡 Отправка запроса на отзыв токенов...")
            logger.info(f"   URL: {revoke_url}")
            logger.info(f"   Payload: client_id={VK_CLIENT_ID}, {log_field}")
            logger.info(f"   Content-Type: application/x-www-form-urlencoded")
            
            # CRITICAL: Используем data= для application/x-www-form-urlencoded, не json=
            response = await client.post(
                revoke_url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0,
            )
            
            logger.info(f"📡 Ответ VK Ads API: {response.status_code}")
            logger.info(f"   Response headers: {dict(response.headers)}")
            
            # Для нечислового логина: при 400 пробуем второй вариант (user_id / username)
            if response.status_code == 400 and not looks_numeric:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error_description") or error_data.get("error", "")
                    logger.debug(f"   Ошибка 400: {error_msg}")
                    if "username" in error_msg.lower() or "invalid" in error_msg.lower():
                        logger.info("   ⚠️ Попытка с username не удалась, пробуем как user_id...")
                        response = await client.post(
                            revoke_url,
                            data={
                                "client_id": VK_CLIENT_ID,
                                "client_secret": VK_CLIENT_SECRET,
                                "user_id": user_id,
                            },
                            headers={"Content-Type": "application/x-www-form-urlencoded"},
                            timeout=30.0,
                        )
                        logger.info(f"   Повторный запрос с user_id: {response.status_code}")
                except Exception:
                    pass
            
            logger.info(f"📡 Ответ VK Ads API: {response.status_code}")
            
            # 200 или 204 означает успешный отзыв (204 = No Content - успешное выполнение без тела ответа)
            if response.status_code in [200, 204]:
                try:
                    response_data = response.json()
                    logger.info(f"✅ Все токены VK Ads успешно отозваны для user_id: {user_id}")
                    logger.info(f"   Ответ API: {response_data}")
                    return True
                except:
                    logger.info(f"✅ Все токены VK Ads успешно отозваны для user_id: {user_id} (статус {response.status_code})")
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
        # Находим пользователя по email (case-insensitive поиск)
        user = db.query(models.User).filter(
            models.User.email.ilike(email)
        ).first()
        
        if not user:
            logger.error(f"❌ Пользователь с email {email} не найден в базе данных")
            logger.info("")
            logger.info("📋 Доступные пользователи в базе данных:")
            all_users = db.query(models.User).all()
            for u in all_users:
                logger.info(f"   - {u.email} (ID: {u.id})")
            logger.info("")
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


async def get_user_id_from_token(access_token: str) -> Optional[str]:
    """
    Получает user_id из access_token через VK Ads API.
    
    Args:
        access_token: Access token VK Ads
        
    Returns:
        Optional[str]: user_id или None при ошибке
    """
    try:
        async with httpx.AsyncClient() as client:
            # Пробуем получить информацию о пользователе через разные endpoints
            endpoints = [
                "https://ads.vk.com/api/v2/statistics/users/summary.json",
                "https://ads.vk.com/api/v2/ad_accounts.json"
            ]
            
            headers = {"Authorization": f"Bearer {access_token}"}
            
            for endpoint in endpoints:
                try:
                    response = await client.get(endpoint, headers=headers, timeout=10.0)
                    if response.status_code == 200:
                        data = response.json()
                        # Пробуем извлечь user_id из ответа
                        # В разных endpoints user_id может быть в разных местах
                        if "user_id" in data:
                            return str(data["user_id"])
                        if "items" in data and len(data["items"]) > 0:
                            item = data["items"][0]
                            if "user_id" in item:
                                return str(item["user_id"])
                            if "id" in item:
                                # id может быть в формате "vkads_USERID@vk@..."
                                id_str = str(item["id"])
                                # Пробуем извлечь user_id из формата
                                import re
                                match = re.search(r'vkads_(\d+)', id_str)
                                if match:
                                    return match.group(1)
                except:
                    continue
            
            # Если не получилось через стандартные endpoints, пробуем через VK ID API
            # (если токен поддерживает это)
            try:
                vk_id_response = await client.get(
                    "https://api.vk.com/method/users.get",
                    params={"access_token": access_token, "v": "5.131"},
                    timeout=10.0
                )
                if vk_id_response.status_code == 200:
                    vk_data = vk_id_response.json()
                    if "response" in vk_data and len(vk_data["response"]) > 0:
                        user_id = vk_data["response"][0].get("id")
                        if user_id:
                            return str(user_id)
            except:
                pass
            
            return None
    except Exception as e:
        logger.debug(f"Ошибка при получении user_id из токена: {e}")
        return None


async def find_all_vk_user_ids_from_tokens() -> List[str]:
    """
    Находит все уникальные vk_user_id из существующих токенов в базе данных.
    Пытается получить user_id из токенов через VK Ads API.
    
    Returns:
        List[str]: Список уникальных vk_user_id
    """
    db = SessionLocal()
    user_ids = set()
    
    try:
        # Находим все интеграции VK Ads
        integrations = db.query(models.Integration).filter(
            models.Integration.platform == models.IntegrationPlatform.VK_ADS,
            models.Integration.access_token.isnot(None)
        ).all()
        
        if not integrations:
            logger.warning("⚠️ Интеграции VK Ads не найдены в базе данных")
            return []
        
        logger.info(f"📋 Найдено {len(integrations)} интеграций VK Ads с токенами")
        logger.info("🔄 Получение user_id из токенов через VK Ads API...")
        
        async def process_integration(integration):
            try:
                # Сначала проверяем, есть ли vk_user_id в БД (если поле существует)
                vk_user_id_from_db = None
                if hasattr(integration, 'vk_user_id'):
                    vk_user_id_from_db = getattr(integration, 'vk_user_id', None)
                    if vk_user_id_from_db:
                        user_ids.add(str(vk_user_id_from_db))
                        logger.info(f"   ✅ Интеграция {integration.id}: используем vk_user_id из БД: {vk_user_id_from_db}")
                        return vk_user_id_from_db
                
                # Пытаемся получить user_id из токена через API
                access_token = security.decrypt_token(integration.access_token)
                user_id = await get_user_id_from_token(access_token)
                if user_id:
                    user_ids.add(user_id)
                    logger.info(f"   ✅ Интеграция {integration.id}: user_id={user_id} (получен из API)")
                    return user_id
                else:
                    logger.warning(f"   ⚠️ Интеграция {integration.id}: не удалось получить user_id из токена")
                    return None
            except Exception as e:
                logger.warning(f"   ⚠️ Ошибка при обработке интеграции {integration.id}: {e}")
                # Если в БД уже есть vk_user_id, используем его
                if hasattr(integration, 'vk_user_id'):
                    vk_user_id_from_db = getattr(integration, 'vk_user_id', None)
                    if vk_user_id_from_db:
                        user_ids.add(str(vk_user_id_from_db))
                        logger.info(f"   ✅ Используем vk_user_id из БД: {vk_user_id_from_db}")
                return None
        
        # Обрабатываем все интеграции асинхронно
        tasks = [process_integration(integration) for integration in integrations]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        if not user_ids:
            logger.warning("⚠️ Не удалось получить ни одного user_id из токенов")
            return []
        
        logger.info(f"✅ Найдено {len(user_ids)} уникальных user_id: {list(user_ids)}")
        return list(user_ids)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при поиске user_id из токенов: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        db.close()


def list_all_vk_integrations() -> None:
    """
    Выводит список всех интеграций VK Ads с их vk_user_id.
    """
    db = SessionLocal()
    try:
        integrations = db.query(models.Integration).join(
            models.Client
        ).join(
            models.User
        ).filter(
            models.Integration.platform == models.IntegrationPlatform.VK_ADS
        ).all()
        
        if not integrations:
            logger.info("📋 Интеграции VK Ads не найдены в базе данных")
            return
        
        logger.info(f"📋 Найдено {len(integrations)} интеграций VK Ads:")
        logger.info("")
        
        for integration in integrations:
            user = integration.client.owner if integration.client else None
            logger.info(f"   Интеграция ID: {integration.id}")
            logger.info(f"   Пользователь: {user.email if user else 'N/A'} (ID: {user.id if user else 'N/A'})")
            logger.info(f"   vk_user_id: {integration.vk_user_id or 'НЕ УСТАНОВЛЕН'}")
            logger.info(f"   account_id: {integration.account_id or 'N/A'}")
            logger.info("")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении списка интеграций: {e}")
        import traceback
        traceback.print_exc()
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
    parser.add_argument(
        "--list",
        action="store_true",
        help="Показать список всех интеграций VK Ads с их vk_user_id"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Отозвать все токены для всех пользователей (получает user_id из токенов через API)"
    )
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="Отозвать все токены для аккаунта приложения (без user_id - удалит только токены приложения)"
    )
    
    args = parser.parse_args()
    
    # Если запрошен список интеграций
    if args.list:
        logger.info("=" * 60)
        logger.info("📋 Список всех интеграций VK Ads")
        logger.info("=" * 60)
        logger.info("")
        list_all_vk_integrations()
        sys.exit(0)
    
    # Проверяем аргументы
    if not args.email and not args.user_id and not args.username and not args.all and not args.force_all:
        parser.error("Необходимо указать email, --user-id, --username, --all или --force-all")
    
    logger.info("=" * 60)
    logger.info("🔄 Отзыв токенов VK Ads")
    logger.info("=" * 60)
    logger.info("")
    
    success_count = 0
    total_count = 0
    
    # Если запрошен принудительный отзыв всех токенов приложения
    if args.force_all:
        logger.info("📌 Принудительный отзыв всех токенов VK Ads для аккаунта приложения")
        logger.warning("   ⚠️ ВНИМАНИЕ: Это удалит токены только для аккаунта приложения!")
        total_count = 1
        if await revoke_vk_tokens_without_user_id():
            success_count = 1
    
    # Если запрошен отзыв всех токенов
    elif args.all:
        logger.info("📌 Отзыв всех токенов VK Ads для всех пользователей")
        logger.info("🔄 Получение user_id из токенов через VK Ads API...")
        user_ids = await find_all_vk_user_ids_from_tokens()
        
        if not user_ids:
            logger.warning("⚠️ Не удалось получить user_id из токенов")
            logger.info("")
            logger.info("📌 Альтернативный вариант: отозвать токены для аккаунта приложения")
            logger.info("   Это удалит токены только для аккаунта приложения, не для всех пользователей.")
            logger.info("")
            logger.info("   Попробуйте:")
            logger.info("   1. Использовать --user-id или --username напрямую")
            logger.info("   2. Или запустить с --force-all для отзыва токенов приложения")
            sys.exit(1)
        
        total_count = len(user_ids)
        
        # Отзываем токены для каждого найденного user_id
        for user_id in user_ids:
            logger.info("")
            logger.info(f"🔄 Отзыв токенов для user_id: {user_id}")
            if await revoke_vk_tokens_by_user_id(user_id):
                success_count += 1
    
    # Если указан user_id напрямую
    elif args.user_id:
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

