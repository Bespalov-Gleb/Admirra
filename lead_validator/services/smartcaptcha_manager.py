"""
Сервис управления Yandex SmartCaptcha через REST API.
Позволяет создавать, обновлять, удалять и получать капчи.

Документация: https://yandex.cloud/ru/docs/smartcaptcha/api-ref/Captcha/

Для работы требуется:
1. IAM-токен (получить через OAuth или сервисный аккаунт)
2. folder_id (ID каталога в Yandex Cloud)
"""

import logging
import json
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger("lead_validator.smartcaptcha_manager")

YANDEX_SMARTCAPTCHA_API = "https://smartcaptcha.api.cloud.yandex.net/smartcaptcha/v1"


class SmartCaptchaManager:
    """
    Менеджер для управления Yandex SmartCaptcha через API.
    """
    
    def __init__(self, iam_token: str = None, folder_id: str = None):
        """
        Инициализация менеджера.
        
        Args:
            iam_token: IAM токен для авторизации (получить через OAuth)
            folder_id: ID каталога Yandex Cloud
        """
        self.iam_token = iam_token
        self.folder_id = folder_id
    
    def _headers(self) -> Dict[str, str]:
        """Заголовки для запросов к API."""
        return {
            "Authorization": f"Bearer {self.iam_token}",
            "Content-Type": "application/json"
        }
    
    async def create_simple_captcha(
        self,
        name: str,
        allowed_sites: List[str] = None,
        complexity: str = "MEDIUM"
    ) -> Dict[str, Any]:
        """
        Создать простую капчу.
        
        Args:
            name: Имя капчи
            allowed_sites: Список разрешённых доменов
            complexity: Сложность (EASY, MEDIUM, HARD)
        
        Returns:
            Ответ API с данными операции
        """
        body = {
            "folderId": self.folder_id,
            "name": name,
            "complexity": complexity
        }
        
        if allowed_sites:
            body["allowedSites"] = allowed_sites
        
        return await self._create_captcha(body)
    
    async def create_advanced_captcha(
        self,
        name: str,
        allowed_sites: List[str],
        security_rules: List[Dict] = None,
        override_variants: List[Dict] = None,
        style_json: Dict = None,
        complexity: str = "HARD",
        pre_check_type: str = "SLIDER",
        challenge_type: str = "IMAGE_TEXT",
        turn_off_hostname_check: bool = True
    ) -> Dict[str, Any]:
        """
        Создать продвинутую капчу с правилами входящего трафика.
        
        Args:
            name: Имя капчи
            allowed_sites: Список разрешённых доменов
            security_rules: Правила безопасности
            override_variants: Варианты заданий
            style_json: Стили оформления
            complexity: Сложность по умолчанию
            pre_check_type: Тип основного задания (CHECKBOX, SLIDER)
            challenge_type: Тип дополнительного задания
            turn_off_hostname_check: Отключить проверку домена
        
        Returns:
            Ответ API с данными операции
        """
        body = {
            "folderId": self.folder_id,
            "name": name,
            "allowedSites": allowed_sites,
            "complexity": complexity,
            "preCheckType": pre_check_type,
            "challengeType": challenge_type,
            "turnOffHostnameCheck": str(turn_off_hostname_check).upper()
        }
        
        if style_json:
            body["styleJson"] = json.dumps(style_json)
        
        if security_rules:
            body["securityRules"] = security_rules
        
        if override_variants:
            body["overrideVariants"] = override_variants
        
        return await self._create_captcha(body)
    
    async def _create_captcha(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Отправить запрос на создание капчи."""
        url = f"{YANDEX_SMARTCAPTCHA_API}/captchas"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    headers=self._headers(),
                    json=body
                )
                
                if response.status_code >= 400:
                    error_data = response.json()
                    logger.error(f"SmartCaptcha API error: {error_data}")
                    return {"error": True, "details": error_data, "status": response.status_code}
                
                return response.json()
                
        except Exception as e:
            logger.error(f"SmartCaptcha API request failed: {e}")
            return {"error": True, "message": str(e)}
    
    async def get_captcha(self, captcha_id: str) -> Dict[str, Any]:
        """Получить информацию о капче по ID."""
        url = f"{YANDEX_SMARTCAPTCHA_API}/captchas/{captcha_id}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=self._headers())
            return response.json()
    
    async def list_captchas(self) -> Dict[str, Any]:
        """Получить список всех капч в каталоге."""
        url = f"{YANDEX_SMARTCAPTCHA_API}/captchas"
        params = {"folderId": self.folder_id}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=self._headers(), params=params)
            return response.json()
    
    async def delete_captcha(self, captcha_id: str) -> Dict[str, Any]:
        """Удалить капчу по ID."""
        url = f"{YANDEX_SMARTCAPTCHA_API}/captchas/{captcha_id}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(url, headers=self._headers())
            return response.json()


def create_example_advanced_captcha_body(folder_id: str) -> Dict[str, Any]:
    """
    Пример тела запроса для создания продвинутой капчи.
    Соответствует документации Yandex Cloud.
    """
    return {
        "folderId": folder_id,
        "name": "advanced-captcha",
        "allowedSites": [
            "example.ru",
            "example.kz"
        ],
        "complexity": "HARD",
        "styleJson": json.dumps({
            "text-color-primary": "#1e1f20",
            "base-background-color": "#c7d0d6",
            "popup-image-container-background-color": "#aab4ba",
            "base-checkbox-background-color": "#5a7080",
            "base-checkbox-background-color-checked": "#5a7080",
            "base-checkbox-border": "2px solid #5a7080",
            "base-checkbox-spin-color": "#5a7080",
            "popup-textinput-background-color": "#c7d0d6",
            "popup-action-button-background-color": "#5a7080",
            "popup-action-button-background-color-hover": "#485863"
        }),
        "turnOffHostnameCheck": "TRUE",
        "preCheckType": "SLIDER",
        "challengeType": "IMAGE_TEXT",
        "securityRules": [
            {
                "name": "rule-1",
                "priority": "11",
                "description": "My first security rule",
                "condition": {
                    "host": {
                        "hosts": [
                            {"exactMatch": "example.com"},
                            {"exactMatch": "example.net"}
                        ]
                    }
                },
                "overrideVariantUuid": "variant-1"
            },
            {
                "name": "rule-2",
                "priority": "12",
                "description": "My second security rule",
                "condition": {
                    "geoIpMatch": {
                        "ipRangesMatch": {
                            "locations": ["ru", "kz"]
                        }
                    }
                },
                "overrideVariantUuid": "variant-2"
            }
        ],
        "overrideVariants": [
            {
                "uuid": "variant-1",
                "description": "Simple variant",
                "complexity": "EASY",
                "preCheckType": "CHECKBOX",
                "challengeType": "SILHOUETTES"
            },
            {
                "uuid": "variant-2",
                "description": "Hard variant",
                "complexity": "HARD",
                "preCheckType": "SLIDER",
                "challengeType": "KALEIDOSCOPE"
            }
        ]
    }


# === CLI USAGE ===
if __name__ == "__main__":
    import asyncio
    import os
    
    async def main():
        # Пример использования
        iam_token = os.getenv("YANDEX_IAM_TOKEN")
        folder_id = os.getenv("YANDEX_FOLDER_ID")
        
        if not iam_token or not folder_id:
            print("❌ Установите переменные окружения:")
            print("   YANDEX_IAM_TOKEN - IAM токен")
            print("   YANDEX_FOLDER_ID - ID каталога")
            print()
            print("Для получения IAM токена:")
            print("   1. Получите OAuth токен: https://oauth.yandex.ru/authorize?response_type=token&client_id=1a6990aa636648e9b2ef855fa7bec2fb")
            print("   2. Обменяйте на IAM: curl -X POST -d '{\"yandexPassportOauthToken\":\"<OAuth>\"}' https://iam.api.cloud.yandex.net/iam/v1/tokens")
            return
        
        manager = SmartCaptchaManager(iam_token, folder_id)
        
        # Список всех капч
        print("📋 Список капч:")
        captchas = await manager.list_captchas()
        print(json.dumps(captchas, indent=2, ensure_ascii=False))
        
        # Создание простой капчи
        # result = await manager.create_simple_captcha("my-test-captcha")
        # print(json.dumps(result, indent=2, ensure_ascii=False))
    
    asyncio.run(main())


