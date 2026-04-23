import httpx
from fastapi import HTTPException
from core import models, schemas
import logging

logger = logging.getLogger(__name__)

class IntegrationService:
    @staticmethod
    async def exchange_vk_token(client_id: str, client_secret: str) -> dict:
        """
        Exchanges VK Ads Client ID and Secret for an Access Token.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://ads.vk.com/api/v2/oauth2/token.json",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": client_id,
                        "client_secret": client_secret
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "access_token": data.get("access_token"),
                        "refresh_token": data.get("refresh_token")
                    }
                else:
                    error_data = response.json()
                    error_msg = error_data.get('error_description') or error_data.get('error') or 'Invalid credentials'
                    raise HTTPException(
                        status_code=400, 
                        detail=f"VK Ads Auth Error: {error_msg}"
                    )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to connect to VK Ads: {str(e)}")

    @staticmethod
    async def refresh_yandex_token(refresh_token: str, client_id: str, client_secret: str) -> dict:
        """
        Refreshes Yandex OAuth access token using a refresh token.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth.yandex.ru/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": client_id,
                        "client_secret": client_secret
                    }
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Yandex Refresh Error: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Failed to refresh Yandex token: {e}")
            return None

    @staticmethod
    async def refresh_vk_token(refresh_token: str, client_id: str, client_secret: str) -> dict:
        """
        Refreshes VK Ads OAuth access token using a refresh token.
        
        Согласно документации VK ID (применимо к VK Ads):
        - Access token живет 1 час (expires_in: 3600)
        - Refresh token используется для получения нового access_token
        - Обмен происходит через ads.vk.com/api/v2/oauth2/token.json с grant_type=refresh_token
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://ads.vk.com/api/v2/oauth2/token.json",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": client_id,
                        "client_secret": client_secret
                    },
                    timeout=30.0
                )
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✅ VK token refreshed successfully")
                    logger.info(f"   New access_token received: {bool(data.get('access_token'))}")
                    logger.info(f"   New refresh_token received: {bool(data.get('refresh_token'))}")
                    logger.info(f"   Expires in: {data.get('expires_in', 'N/A')} seconds")
                    return data
                else:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    error_msg = error_data.get('error_description') or error_data.get('error') or response.text[:200]
                    logger.error(f"❌ VK Refresh Error ({response.status_code}): {error_msg}")
                    return None
        except Exception as e:
            logger.error(f"Failed to refresh VK token: {e}")
            return None

    @staticmethod
    async def revoke_vk_token(
        access_token: str = None, 
        refresh_token: str = None, 
        client_id: str = None,
        client_secret: str = None,
        user_id: str = None
    ) -> bool:
        """
        Отзывает токен доступа VK Ads API согласно официальной документации.
        
        Согласно документации VK Ads API:
        POST /api/v2/oauth2/token/delete.json
        Параметры: client_id, client_secret, username или user_id
        
        Если параметр username/user_id не передан, то будут удалены токены аккаунта,
        для которого был выдан доступ к API.
        
        Args:
            access_token: Access token (не используется напрямую, но сохраняется для логирования)
            refresh_token: Refresh token (не используется напрямую, но сохраняется для логирования)
            client_id: Client ID приложения (обязателен)
            client_secret: Client Secret приложения (обязателен)
            user_id: VK Ads user_id пользователя, для которого нужно удалить токены (опционально)
        
        Returns:
            bool: True если токен успешно отозван или уже неактивен, False при ошибке
        """
        if not client_id or not client_secret:
            logger.warning("⚠️ client_id and client_secret are required for VK Ads token revocation")
            return False
        
        logger.info(f"🔄 Attempting to revoke VK Ads tokens using official API...")
        logger.info(f"   Client ID: {client_id}")
        logger.info(f"   User ID: {user_id or 'N/A (will revoke tokens for token owner)'}")
        
        try:
            async with httpx.AsyncClient() as client:
                # Согласно официальной документации VK Ads API:
                # POST /api/v2/oauth2/token/delete.json
                # Параметры: client_id, client_secret, username или user_id
                revoke_url = "https://ads.vk.com/api/v2/oauth2/token/delete.json"
                
                payload = {
                    "client_id": client_id,
                    "client_secret": client_secret
                }
                
                # Добавляем user_id или username если доступен
                # Если user_id не передан, будут удалены токены аккаунта, для которого был выдан доступ к API
                if user_id:
                    # Проверяем, это числовой ID или username (agency_client format)
                    if user_id.isdigit():
                        payload["user_id"] = user_id
                        logger.info(f"   Revoking tokens for specific user_id: {user_id}")
                    elif '@' in user_id or '_' in user_id:
                        # Это может быть username в формате "login@agency_client" или "vkads_ID@vk@..."
                        payload["username"] = user_id
                        logger.info(f"   Revoking tokens for specific username: {user_id}")
                    else:
                        # Пробуем как username
                        payload["username"] = user_id
                        logger.info(f"   Revoking tokens for username: {user_id}")
                else:
                    logger.info(f"   Revoking tokens for token owner (user_id not provided)")
                
                # CRITICAL: Используем data= для application/x-www-form-urlencoded, не json=
                # Согласно документации VK Ads API, параметры передаются как form data
                response = await client.post(
                    revoke_url,
                    data=payload,  # data= для form-urlencoded
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10.0
                )
                
                logger.info(f"📡 VK Ads token revocation response: {response.status_code}")
                
                # Если получили 400 и использовали username, пробуем как user_id (или наоборот)
                if response.status_code == 400 and user_id:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('error_description') or error_data.get('error', '')
                        logger.debug(f"   First attempt failed: {error_msg}")
                        
                        # Пробуем альтернативный метод
                        alternative_payload = {
                            "client_id": client_id,
                            "client_secret": client_secret
                        }
                        
                        if "username" in payload:
                            # Пробовали username, теперь пробуем user_id
                            alternative_payload["user_id"] = user_id
                            logger.info(f"   Retrying with user_id instead of username...")
                        elif "user_id" in payload:
                            # Пробовали user_id, теперь пробуем username
                            alternative_payload["username"] = user_id
                            logger.info(f"   Retrying with username instead of user_id...")
                        else:
                            # Нечего пробовать
                            alternative_payload = None
                        
                        if alternative_payload:
                            response = await client.post(
                                revoke_url,
                                data=alternative_payload,
                                headers={"Content-Type": "application/x-www-form-urlencoded"},
                                timeout=10.0
                            )
                            logger.info(f"   Retry response: {response.status_code}")
                    except:
                        pass
                
                logger.info(f"📡 Final VK Ads token revocation response: {response.status_code}")
                
                # 200 означает успешный отзыв
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.info(f"✅ VK Ads tokens revoked successfully")
                        logger.info(f"   Response: {response_data}")
                        return True
                    except:
                        logger.info(f"✅ VK Ads tokens revoked successfully (no JSON response)")
                        return True
                
                # 400 может означать, что токены уже недействительны или не найдены (это нормально)
                if response.status_code == 400:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('error_description') or error_data.get('error', '')
                        logger.info(f"ℹ️ VK Ads token revocation returned 400: {error_msg}")
                        # Если токены уже недействительны или не найдены, считаем успешным
                        if 'invalid' in error_msg.lower() or 'not found' in error_msg.lower() or 'expired' in error_msg.lower():
                            logger.info(f"ℹ️ VK Ads tokens already invalid/not found (status 400) - considered revoked")
                            return True
                    except:
                        pass
                    logger.warning(f"⚠️ VK Ads token revocation returned 400: {response.text[:200]}")
                    return False
                
                # 401 означает ошибку авторизации (неверный client_id/client_secret)
                if response.status_code == 401:
                    logger.error(f"❌ VK Ads token revocation failed: Invalid client_id or client_secret (401)")
                    return False
                
                # Другие ошибки
                logger.warning(f"⚠️ VK Ads token revocation returned {response.status_code}: {response.text[:200]}")
                return False
                
        except httpx.RequestError as req_err:
            logger.error(f"❌ Network error revoking VK Ads token: {req_err}")
            return False
        except Exception as e:
            logger.error(f"❌ Error revoking VK Ads token: {e}")
            # Не считаем это критической ошибкой - удаление интеграции должно продолжиться
            return False

    @staticmethod
    def map_error(platform: str, error_detail: str) -> str:
        """
        Maps technical API errors to user-friendly messages.
        """
        # Add mapping logic here as more platforms are added
        return error_detail
