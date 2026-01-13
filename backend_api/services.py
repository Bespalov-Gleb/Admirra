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
    def map_error(platform: str, error_detail: str) -> str:
        """
        Maps technical API errors to user-friendly messages.
        """
        # Add mapping logic here as more platforms are added
        return error_detail
