"""
Проверка наличия телефона в социальных сетях и мессенджерах.

Поддерживаемые методы:
1. VK API (users.search) — бесплатно, поиск по ФИО
2. GetContact неофициальное — имя по телефону (для последующего поиска в VK)
3. GetContact/NumBuster коммерческие — TG, WA, Viber (если есть API)
4. InfoTrackPeople коммерческий — единый запрос по телефону (TG, VK через socials[])

Документация:
- VK API: https://dev.vk.com/ru/method/users.search
- GetContact неофициальное: https://github.com/SijyKijy/GetContactAPI
"""

import logging
import re
import httpx
import json
from typing import Optional
from dataclasses import dataclass, asdict
from lead_validator.config import settings
from lead_validator.services.redis_service import redis_service

logger = logging.getLogger("lead_validator.social_checker")

# Ленивая загрузка GetContact unofficial (опциональная зависимость)
_getcontact_unofficial = None


def _get_getcontact_unofficial():
    global _getcontact_unofficial
    if _getcontact_unofficial is None:
        token = getattr(settings, "GETCONTACT_UNOFFICIAL_TOKEN", "") or ""
        aes = getattr(settings, "GETCONTACT_UNOFFICIAL_AES_KEY", "") or ""
        if token and aes:
            try:
                from lead_validator.services.getcontact_unofficial import GetContactUnofficial
                _getcontact_unofficial = GetContactUnofficial(token, aes)
            except Exception as e:
                logger.warning(f"GetContact unofficial init failed: {e}")
                _getcontact_unofficial = False
        else:
            _getcontact_unofficial = False
    return _getcontact_unofficial if _getcontact_unofficial else None


@dataclass
class SocialCheckResult:
    """Результат проверки телефона в соцсетях"""
    phone: str
    has_telegram: Optional[bool] = None  # TG
    has_whatsapp: Optional[bool] = None  # WA
    has_tiktok: Optional[bool] = None  # TT
    has_vk: Optional[bool] = None  # VK
    has_viber: Optional[bool] = None  # Viber
    
    # Дополнительные данные если найдены
    telegram_username: Optional[str] = None
    vk_profile_url: Optional[str] = None
    vk_user_id: Optional[int] = None
    tiktok_username: Optional[str] = None
    itp_email: Optional[str] = None
    itp_name: Optional[str] = None
    itp_phone: Optional[str] = None
    itp_phones: Optional[list] = None  # list[str], но типизируем мягко для совместимости
    itp_socials: Optional[list] = None  # list[dict]
    
    # Статус проверки
    checked: bool = False
    error: Optional[str] = None
    provider: Optional[str] = None  # Какой провайдер использовался


class SocialChecker:
    """
    Проверка регистрации телефона в социальных сетях.
    
    Поддерживает несколько провайдеров:
    - VK API (бесплатно, ограниченно)
    - GetContact API (платно)
    - NumBuster API (платно)
    """
    
    def __init__(self):
        # VK API настройки
        self.vk_api_token = settings.VK_API_TOKEN  # User OAuth token (users.search недоступен с service token)
        self.vk_api_version = "5.131"
        self.vk_enabled = bool(self.vk_api_token)
        
        # GetContact API коммерческий
        self.getcontact_api_key = settings.GETCONTACT_API_KEY
        self.getcontact_api_url = settings.GETCONTACT_API_URL
        self.getcontact_enabled = bool(self.getcontact_api_key and self.getcontact_api_url)
        
        # GetContact неофициальное (имя по телефону → VK)
        self.getcontact_unofficial_enabled = bool(
            getattr(settings, "GETCONTACT_UNOFFICIAL_TOKEN", "")
            and getattr(settings, "GETCONTACT_UNOFFICIAL_AES_KEY", "")
        )
        
        # NumBuster API настройки
        self.numbuster_api_key = settings.NUMBUSTER_API_KEY
        self.numbuster_api_url = settings.NUMBUSTER_API_URL
        self.numbuster_enabled = bool(self.numbuster_api_key and self.numbuster_api_url)

        # InfoTrackPeople API (коммерческий)
        self.infotrackpeople_api_key = getattr(settings, "INFOTRACKPEOPLE_API_KEY", "") or ""
        self.infotrackpeople_api_url = getattr(settings, "INFOTRACKPEOPLE_API_URL", "") or ""
        self.infotrackpeople_enabled = bool(self.infotrackpeople_api_key and self.infotrackpeople_api_url)
        
        # Общая настройка (VK + любой из GetContact/NumBuster/unofficial)
        self.enabled = (
            self.vk_enabled or self.getcontact_enabled or self.numbuster_enabled
            or self.getcontact_unofficial_enabled
            or self.infotrackpeople_enabled
        )
        
        if not self.enabled:
            logger.debug("Social checker disabled: no API keys configured")
        else:
            providers = []
            if self.vk_enabled:
                providers.append("VK API")
            if self.getcontact_enabled:
                providers.append("GetContact")
            if self.getcontact_unofficial_enabled:
                providers.append("GetContact (unofficial)")
            if self.numbuster_enabled:
                providers.append("NumBuster")
            if self.infotrackpeople_enabled:
                providers.append("InfoTrackPeople")
            logger.info(f"Social checker enabled with providers: {', '.join(providers)}")
    
    def _normalize_phone(self, phone: str) -> str:
        """Нормализует номер телефона для поиска"""
        # Убираем все нецифровые символы кроме +
        cleaned = re.sub(r"[^\d+]", "", phone)
        
        # Если начинается с +7, заменяем на 7
        if cleaned.startswith("+7"):
            cleaned = "7" + cleaned[2:]
        elif cleaned.startswith("8"):
            cleaned = "7" + cleaned[1:]
        
        return cleaned
    
    async def check_phone(
        self,
        phone: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
    ) -> SocialCheckResult:
        """
        Проверяет телефон во всех доступных социальных сетях.
        
        Использует кеширование в Redis для оптимизации повторных запросов.
        
        VK API: поиск только по ФИ/ФИО (имя). Поиск по телефону не поддерживается.
        VK вызывается только если передано name с минимум 2 словами (имя + фамилия).
        
        Args:
            phone: Номер телефона в любом формате
            name: ФИО или ФИ пользователя (опционально). Нужен для поиска в VK.
            
        Returns:
            SocialCheckResult с результатами проверки
        """
        result = SocialCheckResult(phone=phone)
        provider_responded = False
        
        if not self.enabled:
            result.error = "Social checker not configured"
            logger.debug(f"Social check skipped for {phone}: not configured")
            return result
        
        normalized_phone = self._normalize_phone(phone)
        normalized_name = re.sub(r"\s+", " ", (name or "").strip())[:50] if name else ""
        
        # Ключ кеша: при name учитываем его, чтобы не смешивать результаты с/без VK
        normalized_email = (email or "").strip().lower()[:120] if email else ""
        cache_key = (
            f"social_check:v2:{normalized_phone}:n:{normalized_name}:e:{normalized_email}"
            if (normalized_name or normalized_email)
            else f"social_check:v2:{normalized_phone}"
        )
        if redis_service.enabled:
            try:
                cached_result = await redis_service._get_cached_result(cache_key)
                if cached_result:
                    logger.debug(f"Social check cache hit for {phone}")
                    # Восстанавливаем результат из кеша
                    result = SocialCheckResult(**cached_result)
                    return result
            except Exception as e:
                logger.debug(f"Failed to check cache: {e}")
        
        # 0. InfoTrackPeople: единый запрос по телефону -> Telegram/VK
        if self.infotrackpeople_enabled and result.has_telegram is None and result.has_vk is None:
            try:
                itp_result = await self._check_infotrackpeople(normalized_phone, name=name, email=email)
                if itp_result:
                    provider_responded = True
                    result.has_telegram = itp_result.get("has_telegram")
                    result.has_vk = itp_result.get("has_vk")
                    result.has_whatsapp = itp_result.get("has_whatsapp")
                    result.has_viber = itp_result.get("has_viber")
                    result.has_tiktok = itp_result.get("has_tiktok")
                    result.telegram_username = itp_result.get("telegram_username")
                    result.vk_profile_url = itp_result.get("vk_profile_url")
                    result.vk_user_id = itp_result.get("vk_user_id")
                    result.tiktok_username = itp_result.get("tiktok_username")
                    result.itp_email = itp_result.get("email")
                    result.itp_name = itp_result.get("name")
                    result.itp_phone = itp_result.get("phone")
                    result.itp_phones = itp_result.get("phones")
                    result.itp_socials = itp_result.get("socials")

                    if any(
                        v is not None
                        for v in (
                            result.has_telegram,
                            result.has_vk,
                            result.has_whatsapp,
                            result.has_viber,
                            result.has_tiktok,
                        )
                    ):
                        result.provider = "InfoTrackPeople"
                        result.checked = True
                logger.info(
                    "ITP social check for %s: called=%s, has_tg=%s, has_vk=%s, provider=%s",
                    phone,
                    True,
                    result.has_telegram,
                    result.has_vk,
                    result.provider,
                )
            except Exception as e:
                logger.warning(f"InfoTrackPeople check failed for {phone}: {e}")
        elif self.infotrackpeople_enabled:
            logger.debug(
                "ITP skipped for %s because social flags already known: tg=%s vk=%s",
                phone,
                result.has_telegram,
                result.has_vk,
            )

        # 1. Если нет ФИО — пробуем GetContact неофициальное: телефон -> имя -> VK
        search_name = (name or "").strip()
        name_words = search_name.split()
        has_fio = len(name_words) >= 2
        if not has_fio and self.getcontact_unofficial_enabled:
            gc = _get_getcontact_unofficial()
            if gc and gc.enabled:
                try:
                    phone_for_gc = f"+{normalized_phone}" if normalized_phone and not normalized_phone.startswith("+") else normalized_phone or phone
                    country = "RU" if normalized_phone.startswith("7") else "KZ"  # GetContact: RU, KZ, BY, KG, UA
                    fetched_name = await gc.get_name_by_phone(phone_for_gc, country_code=country)
                    if fetched_name:
                        fn_words = fetched_name.strip().split()
                        if len(fn_words) >= 2:
                            search_name = fetched_name.strip()
                            has_fio = True
                            logger.debug(f"GetContact unofficial: {phone} -> name '{search_name}' for VK")
                except Exception as e:
                    logger.debug(f"GetContact unofficial failed for {phone}: {e}")
        
        # 2. VK API — только при наличии ФИ/ФИО (минимум 2 слова). Поиск ТОЛЬКО по фамилия + имя (без отчества).
        # Если InfoTrackPeople уже определил VK (has_vk != None) — повторно не зовём.
        if self.vk_enabled and has_fio and result.has_vk is None:
            vk_search_query = " ".join(name_words[:2])  # Только фамилия и имя
            try:
                vk_result = await self._check_vk_api(vk_search_query, phone=phone)
                if vk_result:
                    provider_responded = True
                    result.has_vk = vk_result.get("has_vk", False)
                    result.vk_user_id = vk_result.get("user_id")
                    result.vk_profile_url = vk_result.get("profile_url")
                    result.provider = "VK API"
                    result.checked = True
            except Exception as e:
                logger.warning(f"VK API check failed for {phone}: {e}")
        elif self.vk_enabled and not has_fio and result.has_vk is None:
            logger.debug(f"VK check skipped for {phone}: no ФИ/ФИО (need at least 2 words in name)")
        
        # 3. GetContact API (платно, более точный)
        if self.getcontact_enabled and not result.checked:
            try:
                getcontact_result = await self._check_getcontact(normalized_phone)
                if getcontact_result:
                    provider_responded = True
                    result.has_telegram = getcontact_result.get("has_telegram")
                    result.has_whatsapp = getcontact_result.get("has_whatsapp")
                    result.has_viber = getcontact_result.get("has_viber")
                    result.telegram_username = getcontact_result.get("telegram_username")
                    result.provider = "GetContact"
                    result.checked = True
                    logger.debug(f"GetContact check for {phone}: TG={result.has_telegram}, WA={result.has_whatsapp}")
            except Exception as e:
                logger.warning(f"GetContact check failed for {phone}: {e}")
        
        # 4. NumBuster API (платно, альтернатива)
        if self.numbuster_enabled and not result.checked:
            try:
                numbuster_result = await self._check_numbuster(normalized_phone)
                if numbuster_result:
                    provider_responded = True
                    result.has_telegram = numbuster_result.get("has_telegram")
                    result.has_whatsapp = numbuster_result.get("has_whatsapp")
                    result.has_tiktok = numbuster_result.get("has_tiktok")
                    result.provider = "NumBuster"
                    result.checked = True
                    logger.debug(f"NumBuster check for {phone}: TG={result.has_telegram}, WA={result.has_whatsapp}")
            except Exception as e:
                logger.warning(f"NumBuster check failed for {phone}: {e}")

        # 5. Telegram через Telethon (опционально, если has_telegram ещё не определён)
        if result.has_telegram is None:
            try:
                from lead_validator.services.telegram_checker import check_phone_registered
                tg_reg = await check_phone_registered(phone)
                if tg_reg is not None:
                    provider_responded = True
                    result.has_telegram = tg_reg
                    if not result.checked:
                        result.checked = True
                        result.provider = "Telethon"
                    logger.debug(f"Telethon Telegram check for {phone}: {result.has_telegram}")
            except Exception as e:
                logger.debug(f"Telethon Telegram check failed: {e}")
        
        if not result.checked:
            if provider_responded:
                # Провайдер(ы) ответили, но соцпрофили не обнаружены.
                result.error = "No social profiles found"
                logger.debug(f"Social providers responded but no profiles found for {phone}")
            else:
                result.error = "All providers failed or unavailable"
                logger.debug(f"All social check providers failed for {phone}")
        
        # Сохраняем результат в кеш (TTL 7 дней = 604800 секунд)
        if redis_service.enabled and result.checked:
            try:
                cache_data = asdict(result)
                await redis_service._cache_result(cache_key, cache_data, ttl=604800)
                logger.debug(f"Cached social check result for {phone}")
            except Exception as e:
                logger.debug(f"Failed to cache result: {e}")
        
        return result
    
    async def _check_vk_api(self, search_query: str, phone: str = "") -> Optional[dict]:
        """
        Проверка через VK API users.search.
        
        Поиск только по фамилия + имя (без отчества).
        Документация: https://dev.vk.com/ru/method/users.search
        
        Returns:
            dict с результатами или None при ошибке
        """
        if not self.vk_api_token:
            logger.info("[VK] Поиск не начат: VK_API_TOKEN не задан")
            return None

        logger.info(f"[VK] Поиск НАЧАТ: q='{search_query}' (телефон {phone or '-'})")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = "https://api.vk.com/method/users.search"
                params = {
                    "q": search_query,
                    "fields": "photo_100,domain",
                    "count": 1,
                    "access_token": self.vk_api_token,
                    "v": self.vk_api_version
                }
                
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    logger.warning(f"[VK] Поиск ЗАВЕРШЁН с ошибкой: HTTP {response.status_code}")
                    return None

                data = response.json()
                
                if "error" in data:
                    error_code = data["error"].get("error_code")
                    error_msg = data["error"].get("error_msg", "")
                    if error_code == 5:
                        logger.warning("[VK] Поиск ЗАВЕРШЁН: Invalid token, проверьте VK_API_TOKEN")
                    elif error_code == 1051:
                        logger.warning(
                            "[VK] Поиск ЗАВЕРШЁН: users.search недоступен с сервисным ключом. "
                            "Требуется пользовательский OAuth-токен. См. https://qna.habr.com/q/472088"
                        )
                    else:
                        logger.warning(f"[VK] Поиск ЗАВЕРШЁН с ошибкой API: [{error_code}] {error_msg}")
                    return None
                
                if "response" not in data:
                    logger.info("[VK] Поиск ЗАВЕРШЁН: неожиданный формат ответа (нет response)")
                    return {"has_vk": False}

                items = data["response"].get("items", [])
                count = data["response"].get("count", 0)
                
                if items:
                    user = items[0]
                    user_id = user.get("id")
                    domain = user.get("domain") or f"id{user_id}"
                    profile_url = f"https://vk.com/{domain}"
                    logger.info(f"[VK] Поиск ЗАВЕРШЁН: НАЙДЕН profile_url={profile_url} (user_id={user_id}, всего совпадений: {count})")
                    return {
                        "has_vk": True,
                        "user_id": user_id,
                        "profile_url": profile_url
                    }
                
                # Пустой результат
                reason = "профиль не найден или скрыт настройками приватности" if count == 0 else "items пуст (возможна фильтрация по возрасту/другое)"
                logger.info(f"[VK] Поиск ЗАВЕРШЁН: НЕ НАЙДЕН. Причина: {reason} (count={count})")
                return {"has_vk": False}
                
        except httpx.TimeoutException:
            logger.warning(f"[VK] Поиск ЗАВЕРШЁН: timeout при запросе для q='{search_query[:40]}...'")
            return None
        except Exception as e:
            logger.error(f"[VK] Поиск ЗАВЕРШЁН с исключением: {e}")
            return None

    async def _check_infotrackpeople(
        self,
        phone: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Проверка через InfoTrackPeople API.

        По докам:
          - POST /public-api/data/search
          - Header: x-api-key
          - Body: {"searchOptions":[{"type":"phone","query":...},{"type":"name","query":...},{"type":"email","query":...}]}
        """
        if not self.infotrackpeople_enabled:
            return None

        try:
            from lead_validator.services.infotrackpeople_checker import InfoTrackPeopleChecker

            itp = InfoTrackPeopleChecker(
                api_key=self.infotrackpeople_api_key,
                search_url=self.infotrackpeople_api_url,
            )
            phone_query = phone if str(phone).startswith("+") else f"+{phone}"
            itp_res = await itp.check_phone(phone_query, name=name, email=email)
            if itp_res is None:
                return None

            return {
                "has_telegram": itp_res.has_telegram,
                "has_vk": itp_res.has_vk,
                "has_whatsapp": itp_res.has_whatsapp,
                "has_viber": itp_res.has_viber,
                "has_tiktok": itp_res.has_tiktok,
                "telegram_username": itp_res.telegram_username,
                "vk_profile_url": itp_res.vk_profile_url,
                "vk_user_id": itp_res.vk_user_id,
                "tiktok_username": itp_res.tiktok_username,
                "email": itp_res.email,
                "name": itp_res.name,
                "phone": itp_res.phone,
                "phones": itp_res.phones,
                "socials": itp_res.socials,
            }
        except Exception as e:
            logger.warning(f"InfoTrackPeople request failed for {phone}: {e}")
            return None
    
    async def _check_getcontact(self, phone: str) -> Optional[dict]:
        """
        Проверка через GetContact API.
        
        Документация: https://getcontact.com/api
        
        Требуется:
        - API ключ от GetContact
        - Платный тариф
        
        Returns:
            dict с результатами или None при ошибке
        """
        if not self.getcontact_api_key or not self.getcontact_api_url:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = self.getcontact_api_url
                headers = {
                    "Authorization": f"Bearer {self.getcontact_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "phone": phone
                }
                
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        "has_telegram": data.get("telegram", False),
                        "has_whatsapp": data.get("whatsapp", False),
                        "has_viber": data.get("viber", False),
                        "telegram_username": data.get("telegram_username")
                    }
                elif response.status_code == 401:
                    logger.warning("GetContact API: Invalid API key")
                    return None
                elif response.status_code == 402:
                    logger.warning("GetContact API: Insufficient funds")
                    return None
                else:
                    logger.warning(f"GetContact API returned status {response.status_code}")
                    return None
                    
        except httpx.TimeoutException:
            logger.warning(f"GetContact API timeout for phone {phone}")
            return None
        except Exception as e:
            logger.error(f"GetContact API check error: {e}")
            return None
    
    async def _check_numbuster(self, phone: str) -> Optional[dict]:
        """
        Проверка через NumBuster API.
        
        Документация: https://numbuster.com/api
        
        Требуется:
        - API ключ от NumBuster
        - Платный тариф
        
        Returns:
            dict с результатами или None при ошибке
        """
        if not self.numbuster_api_key or not self.numbuster_api_url:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = self.numbuster_api_url
                headers = {
                    "Authorization": f"Bearer {self.numbuster_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "phone": phone
                }
                
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        "has_telegram": data.get("telegram", False),
                        "has_whatsapp": data.get("whatsapp", False),
                        "has_tiktok": data.get("tiktok", False)
                    }
                elif response.status_code == 401:
                    logger.warning("NumBuster API: Invalid API key")
                    return None
                elif response.status_code == 402:
                    logger.warning("NumBuster API: Insufficient funds")
                    return None
                else:
                    logger.warning(f"NumBuster API returned status {response.status_code}")
                    return None
                    
        except httpx.TimeoutException:
            logger.warning(f"NumBuster API timeout for phone {phone}")
            return None
        except Exception as e:
            logger.error(f"NumBuster API check error: {e}")
            return None
    
    async def check_telegram(self, phone: str) -> Optional[bool]:
        """
        Проверка регистрации в Telegram.
        
        Возможные методы:
        1. Telegram Bot API (requires user interaction)
        2. Сторонние чекеры (GetContact, NumBuster)
        3. MTProto API (сложная интеграция)
        """
        if not self.enabled:
            return None
        
        result = await self.check_phone(phone)
        return result.has_telegram
    
    async def check_whatsapp(self, phone: str) -> Optional[bool]:
        """
        Проверка регистрации в WhatsApp.
        
        Методы:
        1. WhatsApp Business API (официальный, требует верификации)
        2. Сторонние чекеры (GetContact, NumBuster)
        """
        if not self.enabled:
            return None
        
        result = await self.check_phone(phone)
        return result.has_whatsapp
    
    async def check_vk(self, phone: str) -> Optional[bool]:
        """
        Проверка регистрации в VK.
        
        Методы:
        1. VK API users.search (ограниченный функционал)
        2. Сторонние сервисы
        """
        if not self.enabled:
            return None
        
        result = await self.check_phone(phone)
        return result.has_vk


# Глобальный экземпляр
social_checker = SocialChecker()
