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
    def map_error(platform: str, error_detail: str) -> str:
        """
        Maps technical API errors to user-friendly messages.
        """
        # Add mapping logic here as more platforms are added
        return error_detail
