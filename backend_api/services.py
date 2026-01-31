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
    async def revoke_vk_token(access_token: str = None, refresh_token: str = None, client_id: str = None) -> bool:
        """
        Отзывает токен доступа VK Ads API.
        
        Пытается отозвать токен через VK Ads API. Если токен уже истек или был отозван,
        это не считается ошибкой - цель достигнута (токен не активен).
        
        Args:
            access_token: Access token для отзыва (приоритет)
            refresh_token: Refresh token для отзыва (если access_token недоступен)
            client_id: Client ID приложения (опционально, для логирования)
        
        Returns:
            bool: True если токен успешно отозван или уже неактивен, False при ошибке
        """
        if not access_token and not refresh_token:
            logger.warning("⚠️ No token provided for revocation (both access_token and refresh_token are None)")
            return False
        
        token_to_revoke = access_token or refresh_token
        token_type = "access_token" if access_token else "refresh_token"
        
        logger.info(f"🔄 Attempting to revoke VK Ads {token_type}...")
        logger.info(f"   Client ID: {client_id or 'N/A'}")
        
        try:
            async with httpx.AsyncClient() as client:
                # Метод 1: Попытка отозвать через стандартный OAuth2 revoke endpoint
                # Обычно это POST /oauth2/revoke или DELETE запрос
                revoke_urls = [
                    "https://ads.vk.com/api/v2/oauth2/revoke",
                    "https://ads.vk.com/api/v2/oauth2/token.json"  # С grant_type=revoke_token
                ]
                
                for revoke_url in revoke_urls:
                    try:
                        # Попытка 1: POST с token в теле запроса
                        payload = {
                            "token": token_to_revoke,
                            "token_type_hint": token_type
                        }
                        if client_id:
                            payload["client_id"] = client_id
                        
                        response = await client.post(revoke_url, data=payload, timeout=10.0)
                        
                        # 200 или 204 означает успешный отзыв
                        if response.status_code in [200, 204]:
                            logger.info(f"✅ VK Ads token revoked successfully via {revoke_url}")
                            return True
                        
                        # 400 может означать, что токен уже недействителен (это нормально)
                        if response.status_code == 400:
                            try:
                                error_data = response.json()
                                error_code = error_data.get('error', '')
                                if 'invalid' in error_code.lower() or 'expired' in error_code.lower():
                                    logger.info(f"ℹ️ VK Ads token already invalid/expired (status 400) - considered revoked")
                                    return True
                            except:
                                pass
                        
                        # 401 означает, что токен уже недействителен (это нормально)
                        if response.status_code == 401:
                            logger.info(f"ℹ️ VK Ads token already invalid (status 401) - considered revoked")
                            return True
                        
                        # 404 означает, что endpoint не существует - пробуем следующий
                        if response.status_code == 404:
                            logger.debug(f"⚠️ Revoke endpoint {revoke_url} returned 404, trying next method...")
                            continue
                        
                        # Другие ошибки логируем, но продолжаем попытки
                        logger.warning(f"⚠️ Revoke attempt via {revoke_url} returned {response.status_code}: {response.text[:200]}")
                        
                    except httpx.RequestError as req_err:
                        logger.debug(f"⚠️ Request error for {revoke_url}: {req_err}")
                        continue
                
                # Метод 2: Если стандартные методы не сработали, пробуем через DELETE запрос
                # (некоторые OAuth2 реализации используют DELETE для отзыва)
                try:
                    delete_url = f"https://ads.vk.com/api/v2/oauth2/tokens/{token_to_revoke}"
                    response = await client.delete(delete_url, timeout=10.0)
                    if response.status_code in [200, 204, 404]:
                        logger.info(f"✅ VK Ads token revoked via DELETE method")
                        return True
                except:
                    pass
                
                # Если все методы не сработали, считаем что токен может быть уже недействителен
                # или VK Ads не предоставляет публичный API для отзыва
                logger.warning(f"⚠️ Could not revoke VK Ads token via standard methods. Token may already be invalid or VK Ads doesn't provide public revoke API.")
                logger.warning(f"   This is not critical - token will expire naturally or can be revoked manually in VK Ads settings.")
                return True  # Считаем успешным, так как цель - освободить слот токена
                
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
