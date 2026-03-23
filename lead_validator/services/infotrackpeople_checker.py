"""
Интеграция InfoTrackPeople (ITP).

Делает единый запрос по телефону и пытается извлечь из ответа:
- Telegram (социальные/мессенджерные профили)
- VK (профиль в ВК)

Docs:
- Search: POST /public-api/data/search
- Auth: заголовок x-api-key
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

import httpx
from lead_validator.config import settings

logger = logging.getLogger("lead_validator.infotrackpeople")


def _extract_telegram_username(url: str) -> Optional[str]:
    # Пример: https://t.me/username или https://t.me/username/
    if not url:
        return None
    m = re.search(r"(?:t\.me|telegram\.me)/([A-Za-z0-9_]{3,32})", url)
    if m:
        return m.group(1)
    return None


def _extract_vk_user_id(url: str) -> Optional[int]:
    """
    Пытаемся вытащить id из URL вида:
    - https://vk.com/id123
    - https://vk.com/club123
    """
    if not url:
        return None
    m = re.search(r"vk\.com/(id|club)(\d+)", url)
    if not m:
        return None
    try:
        return int(m.group(2))
    except ValueError:
        return None


def _extract_vk_user_id_from_field(value) -> Optional[int]:
    if value is None:
        return None
    try:
        text = str(value).strip()
        if not text:
            return None
        if text.isdigit():
            return int(text)
        m = re.search(r"(\d+)", text)
        if m:
            return int(m.group(1))
    except Exception:
        return None
    return None


@dataclass
class InfoTrackPeopleResult:
    has_telegram: Optional[bool] = None
    has_vk: Optional[bool] = None
    telegram_username: Optional[str] = None
    vk_profile_url: Optional[str] = None
    vk_user_id: Optional[int] = None


class InfoTrackPeopleChecker:
    def __init__(self, api_key: str, search_url: str):
        self.api_key = (api_key or "").strip()
        self.search_url = (search_url or "").strip()

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.search_url)

    async def check_phone(self, phone: str) -> Optional[InfoTrackPeopleResult]:
        """
        Returns:
            InfoTrackPeopleResult или None если запрос недоступен/ничего не найдено.
        """
        if not self.enabled:
            return None

        payload = {
            "searchOptions": [
                {
                    "type": "phone",
                    "query": phone,
                }
            ]
        }

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(self.search_url, json=payload, headers=headers)
                if resp.status_code != 200:
                    err_msg = None
                    try:
                        err = resp.json().get("error", {})
                        if isinstance(err, dict):
                            err_msg = err.get("message") or err.get("key")
                    except Exception:
                        err_msg = None
                    logger.warning(
                        "ITP search failed: HTTP %s for phone=%s (%s)",
                        resp.status_code,
                        phone,
                        err_msg or "unknown error",
                    )
                    return None
                data = resp.json()
        except httpx.TimeoutException:
            logger.warning("ITP search timeout for phone=%s", phone)
            return None
        except Exception as e:
            logger.warning("ITP search exception for phone=%s: %s", phone, e)
            return None

        if not isinstance(data, dict):
            return None

        if getattr(settings, "INFOTRACKPEOPLE_LOG_RAW", False):
            try:
                # Ограничиваем размер лога, чтобы не раздувать логи.
                raw_preview = str(data)
                if len(raw_preview) > 4000:
                    raw_preview = raw_preview[:4000] + "...<truncated>"
                logger.info("ITP raw response for phone=%s: %s", phone, raw_preview)
            except Exception:
                pass

        data_block = data.get("data")
        if not isinstance(data_block, dict):
            return None

        logger.info(
            "ITP response meta for phone=%s: searchId=%s, records=%s, db_blocks=%s",
            phone,
            data.get("searchId"),
            data.get("records"),
            len(data_block),
        )

        # Находим любые записи по телефону.
        found_records = False

        # Флаги, чтобы отличать "не нашли" от "нашли, но соцсети не указаны в полях".
        found_telegram = False
        found_vk = False
        telegram_username: Optional[str] = None
        vk_profile_url: Optional[str] = None
        vk_user_id: Optional[int] = None
        any_socials_field_seen = False

        for _db_name, db_payload in data_block.items():
            if not isinstance(db_payload, dict):
                continue
            records = db_payload.get("data")
            if not isinstance(records, list):
                continue
            if records:
                found_records = True

            for record in records:
                if not isinstance(record, dict):
                    continue
                socials = record.get("socials")
                if socials is None or not isinstance(socials, list):
                    socials = []
                else:
                    any_socials_field_seen = True

                for social in socials:
                    if not isinstance(social, dict):
                        continue
                    title = str(social.get("title") or "").strip()
                    url = str(social.get("url") or "").strip()
                    title_l = title.lower()

                    # Telegram
                    if "telegram" in title_l or title_l == "tg":
                        found_telegram = True
                        u = _extract_telegram_username(url)
                        if u:
                            telegram_username = u
                        continue

                    # VK (ВКонтакте)
                    if (
                        "vkontakte" in title_l
                        or "вконтакте" in title_l
                        or "vk" in title_l
                    ):
                        found_vk = True
                        if url:
                            vk_profile_url = url
                            vk_user_id = _extract_vk_user_id(url)
                        continue

                # Fallback поля v1/v2, если socials пустой/неполный
                tg_username = (
                    record.get("tg_username")
                    or record.get("telegram_username")
                    or (
                        record.get("username")
                        if str(record.get("username") or "").strip() and "@" not in str(record.get("username") or "")
                        else None
                    )
                )
                if isinstance(tg_username, str) and tg_username.strip():
                    found_telegram = True
                    if not telegram_username:
                        telegram_username = tg_username.strip().lstrip("@")
                    any_socials_field_seen = True

                telegram_url = (
                    record.get("telegram_url")
                    or record.get("telegram")
                    or record.get("tg")
                )
                if isinstance(telegram_url, str) and telegram_url.strip():
                    maybe_tg = _extract_telegram_username(telegram_url.strip())
                    if maybe_tg:
                        found_telegram = True
                        telegram_username = telegram_username or maybe_tg
                        any_socials_field_seen = True

                vk_url = record.get("vk_url") or record.get("vk_profile_url") or record.get("vk")
                if isinstance(vk_url, str) and vk_url.strip():
                    found_vk = True
                    vk_profile_url = vk_profile_url or vk_url.strip()
                    vk_user_id = vk_user_id or _extract_vk_user_id(vk_profile_url)
                    any_socials_field_seen = True

                vk_id_raw = record.get("vk_id")
                if vk_user_id is None and vk_id_raw is not None:
                    parsed_vk_id = _extract_vk_user_id_from_field(vk_id_raw)
                    if parsed_vk_id is not None:
                        found_vk = True
                        vk_user_id = parsed_vk_id
                        if not vk_profile_url:
                            vk_profile_url = f"https://vk.com/id{parsed_vk_id}"
                        any_socials_field_seen = True

        if not found_records:
            return None

        res = InfoTrackPeopleResult()
        # Если поле socials встречалось в данных, то отсутствие Telegram/VK считаем False.
        # Если поле socials не встречалось вовсе, оставляем None (неизвестно).
        if any_socials_field_seen:
            res.has_telegram = found_telegram
            res.has_vk = found_vk
            res.telegram_username = telegram_username
            res.vk_profile_url = vk_profile_url
            res.vk_user_id = vk_user_id
        else:
            res.has_telegram = None
            res.has_vk = None

        logger.info(
            "ITP parsed socials for phone=%s: has_tg=%s, has_vk=%s, tg_username=%s, vk_url=%s, vk_id=%s",
            phone,
            res.has_telegram,
            res.has_vk,
            bool(res.telegram_username),
            bool(res.vk_profile_url),
            res.vk_user_id,
        )

        return res

