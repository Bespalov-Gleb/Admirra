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
from typing import Optional, List, Set, Dict, Any

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


def _extract_tiktok_username(url: str) -> Optional[str]:
    """
    Извлекаем username из ссылок вида:
    - https://www.tiktok.com/@username
    - https://tiktok.com/@username
    """
    if not url:
        return None
    # Username обычно состоит из букв/цифр/подчеркиваний/точек.
    m = re.search(r"tiktok\.com/(?:@)?([A-Za-z0-9_\.]{2,24})", url)
    if m:
        return m.group(1)
    return None


@dataclass
class InfoTrackPeopleResult:
    has_telegram: Optional[bool] = None
    has_vk: Optional[bool] = None
    has_whatsapp: Optional[bool] = None
    has_viber: Optional[bool] = None
    has_tiktok: Optional[bool] = None
    telegram_username: Optional[str] = None
    vk_profile_url: Optional[str] = None
    vk_user_id: Optional[int] = None
    tiktok_username: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    phones: Optional[List[str]] = None
    socials: Optional[List[dict]] = None


class InfoTrackPeopleChecker:
    def __init__(self, api_key: str, search_url: str):
        self.api_key = (api_key or "").strip()
        self.search_url = (search_url or "").strip()

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.search_url)

    async def _search(self, payload: dict, phone: str) -> Optional[dict]:
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
                return resp.json()
        except httpx.TimeoutException:
            logger.warning("ITP search timeout for phone=%s", phone)
            return None
        except Exception as e:
            logger.warning("ITP search exception for phone=%s: %s", phone, e)
            return None

    async def check_phone(
        self,
        phone: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Optional[InfoTrackPeopleResult]:
        """
        Returns:
            InfoTrackPeopleResult или None если запрос недоступен/ничего не найдено.
        """
        if not self.enabled:
            return None

        digits_only = (
            "".join(filter(str.isdigit, phone)) if isinstance(phone, str) and phone else ""
        )

        phone_text = phone.strip() if isinstance(phone, str) else ""
        normalized_name = re.sub(r"\s+", " ", name).strip() if isinstance(name, str) and name.strip() else ""
        normalized_email = email.strip() if isinstance(email, str) and email.strip() and "@" in email else ""

        # Общий текстовый запрос для "широкого" матчинга.
        full_text_parts = []
        if digits_only:
            full_text_parts.append(digits_only)
        if phone_text:
            full_text_parts.append(phone_text)
        if normalized_name:
            full_text_parts.append(normalized_name)
        if normalized_email:
            full_text_parts.append(normalized_email)
        full_text_query = " ".join(full_text_parts).strip()

        # Варианты payload: ITP по-разному индексирует phone/full_text.
        payloads: List[dict] = []

        opts_digits: List[dict] = []
        if digits_only:
            opts_digits.append({"type": "phone", "query": digits_only})
        elif phone_text:
            opts_digits.append({"type": "phone", "query": phone_text})
        if normalized_name:
            opts_digits.append({"type": "name", "query": normalized_name})
        if normalized_email:
            opts_digits.append({"type": "email", "query": normalized_email})
        if full_text_query:
            opts_digits.append({"type": "full_text", "query": full_text_query})
        if opts_digits:
            payloads.append({"searchOptions": opts_digits})

        # Альтернатива с phone как исходной строкой (+7...)
        if phone_text and digits_only and phone_text != digits_only:
            opts_phone_text: List[dict] = [{"type": "phone", "query": phone_text}]
            if normalized_name:
                opts_phone_text.append({"type": "name", "query": normalized_name})
            if normalized_email:
                opts_phone_text.append({"type": "email", "query": normalized_email})
            if full_text_query:
                opts_phone_text.append({"type": "full_text", "query": full_text_query})
            payloads.append({"searchOptions": opts_phone_text})

        # Отдельный full_text-only пробуем всегда, если есть query
        if full_text_query:
            payloads.append({"searchOptions": [{"type": "full_text", "query": full_text_query}]})

        responses: List[dict] = []
        for idx, payload in enumerate(payloads, start=1):
            data = await self._search(payload, phone)
            if not isinstance(data, dict):
                continue
            responses.append(data)
            if getattr(settings, "INFOTRACKPEOPLE_LOG_RAW", False):
                try:
                    raw_preview = str(data)
                    if len(raw_preview) > 4000:
                        raw_preview = raw_preview[:4000] + "...<truncated>"
                    logger.info("ITP raw response #%s for phone=%s: %s", idx, phone, raw_preview)
                except Exception:
                    pass

        if not responses:
            return None

        # Мержим data-блоки из всех успешных ответов в единый набор.
        merged_data_block: Dict[str, Any] = {}
        merged_records = 0
        for idx, data in enumerate(responses, start=1):
            try:
                merged_records += int(data.get("records") or 0)
            except Exception:
                pass
            block = data.get("data")
            if not isinstance(block, dict):
                continue
            for db_name, db_payload in block.items():
                key = str(db_name)
                if key in merged_data_block:
                    key = f"{key}#{idx}"
                merged_data_block[key] = db_payload

        if not merged_data_block:
            return None

        data_block = merged_data_block

        logger.info(
            "ITP response meta for phone=%s (name=%s, email=%s): payloads=%s, merged_records=%s, db_blocks=%s",
            phone,
            bool(name and str(name).strip()),
            bool(email and str(email).strip()),
            len(payloads),
            merged_records,
            len(data_block),
        )

        # Находим любые записи по телефону.
        found_records = False

        # Флаги, чтобы отличать "не нашли" от "нашли, но соцсети не указаны в полях".
        found_telegram = False
        found_vk = False
        found_whatsapp = False
        found_viber = False
        found_tiktok = False
        telegram_username: Optional[str] = None
        vk_profile_url: Optional[str] = None
        vk_user_id: Optional[int] = None
        tiktok_username: Optional[str] = None
        any_socials_field_seen = False
        extracted_email: Optional[str] = None
        extracted_name: Optional[str] = None
        extracted_phone: Optional[str] = None
        extracted_phones: Set[str] = set()
        itp_socials: List[dict] = []
        itp_socials_seen: Set[tuple] = set()
        observed_fields: Set[str] = set()

        def _pick_first_nonempty(*values) -> Optional[str]:
            for v in values:
                if isinstance(v, str) and v.strip():
                    return v.strip()
            return None

        def _normalize_email(email_val: str) -> Optional[str]:
            e = (email_val or "").strip()
            if not e or "@" not in e:
                return None
            return e

        def _add_phones(value) -> None:
            if value is None:
                return
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        s = item.strip()
                        if s:
                            extracted_phones.add(s)
                return
            if isinstance(value, str):
                s = value.strip()
                if s:
                    extracted_phones.add(s)

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
                observed_fields.update(record.keys())
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

                    # Сохраняем все соцсети (кроме дубликатов) для "все соцсети"
                    if title or url:
                        key = (title_l, url)
                        if key not in itp_socials_seen:
                            itp_socials_seen.add(key)
                            itp_socials.append({"title": title, "url": url})

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

                    # WhatsApp
                    if "whatsapp" in title_l:
                        found_whatsapp = True
                        continue

                    # Viber
                    if "viber" in title_l:
                        found_viber = True
                        continue

                    # TikTok
                    if "tiktok" in title_l:
                        found_tiktok = True
                        if url and not tiktok_username:
                            tiktok_username = _extract_tiktok_username(url)
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

                # Email / name / phone (часто есть в v1/v2 блоках)
                if not extracted_email:
                    email_candidate = _pick_first_nonempty(
                        record.get("email"),
                        record.get("mail"),
                        record.get("email_address"),
                    )
                    if email_candidate:
                        extracted_email = _normalize_email(email_candidate)
                if not extracted_name:
                    extracted_name = _pick_first_nonempty(
                        record.get("name"),
                        record.get("fio"),
                        record.get("full_name"),
                    )
                if not extracted_phone:
                    extracted_phone = _pick_first_nonempty(
                        record.get("phone"),
                        record.get("phone_number"),
                    )
                _add_phones(record.get("phone"))
                _add_phones(record.get("phone_number"))

        if not found_records:
            return None

        has_useful_data = bool(
            any_socials_field_seen
            or extracted_email
            or extracted_name
            or extracted_phone
            or extracted_phones
            or telegram_username
            or vk_profile_url
            or vk_user_id is not None
        )

        if not has_useful_data:
            full_text_parts = []
            if digits_only:
                full_text_parts.append(digits_only)
            if isinstance(phone, str) and phone.strip():
                full_text_parts.append(phone.strip())
            if isinstance(name, str) and name.strip():
                full_text_parts.append(re.sub(r"\s+", " ", name).strip())
            if isinstance(email, str) and email.strip() and "@" in email:
                full_text_parts.append(email.strip())
            full_text_query = " ".join(full_text_parts).strip()

            if full_text_query:
                logger.info("ITP fallback full_text request for phone=%s", phone)
                fallback_data = await self._search(
                    {"searchOptions": [{"type": "full_text", "query": full_text_query}]},
                    phone,
                )
                if isinstance(fallback_data, dict):
                    fallback_block = fallback_data.get("data")
                    if isinstance(fallback_block, dict):
                        for _db_name, db_payload in fallback_block.items():
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
                                observed_fields.update(record.keys())

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

                                    # Сохраняем все соцсети (кроме дубликатов) для "все соцсети"
                                    if title or url:
                                        key = (title_l, url)
                                        if key not in itp_socials_seen:
                                            itp_socials_seen.add(key)
                                            itp_socials.append({"title": title, "url": url})

                                    if "telegram" in title_l or title_l == "tg":
                                        found_telegram = True
                                        u = _extract_telegram_username(url)
                                        if u and not telegram_username:
                                            telegram_username = u
                                        continue

                                    if (
                                        "vkontakte" in title_l
                                        or "вконтакте" in title_l
                                        or "vk" in title_l
                                    ):
                                        found_vk = True
                                        if url and not vk_profile_url:
                                            vk_profile_url = url
                                        if vk_user_id is None and vk_profile_url:
                                            vk_user_id = _extract_vk_user_id(vk_profile_url)
                                        continue

                                    if "whatsapp" in title_l:
                                        found_whatsapp = True
                                        continue

                                    if "viber" in title_l:
                                        found_viber = True
                                        continue

                                    if "tiktok" in title_l:
                                        found_tiktok = True
                                        if url and not tiktok_username:
                                            tiktok_username = _extract_tiktok_username(url)
                                        continue

                                if not extracted_email:
                                    email_candidate = _pick_first_nonempty(
                                        record.get("email"),
                                        record.get("mail"),
                                        record.get("email_address"),
                                    )
                                    if email_candidate:
                                        extracted_email = _normalize_email(email_candidate)
                                if not extracted_name:
                                    extracted_name = _pick_first_nonempty(
                                        record.get("name"),
                                        record.get("fio"),
                                        record.get("full_name"),
                                    )
                                if not extracted_phone:
                                    extracted_phone = _pick_first_nonempty(
                                        record.get("phone"),
                                        record.get("phone_number"),
                                    )
                                _add_phones(record.get("phone"))
                                _add_phones(record.get("phone_number"))

        res = InfoTrackPeopleResult()
        # Если поле socials встречалось в данных, то отсутствие Telegram/VK считаем False.
        # Если поле socials не встречалось вовсе, оставляем None (неизвестно).
        if any_socials_field_seen:
            res.has_telegram = found_telegram
            res.has_vk = found_vk
            res.has_whatsapp = found_whatsapp
            res.has_viber = found_viber
            res.has_tiktok = found_tiktok
            res.telegram_username = telegram_username
            res.vk_profile_url = vk_profile_url
            res.vk_user_id = vk_user_id
            res.tiktok_username = tiktok_username
        else:
            res.has_telegram = None
            res.has_vk = None
            res.has_whatsapp = None
            res.has_viber = None
            res.has_tiktok = None

        res.email = extracted_email
        res.name = extracted_name
        res.phone = extracted_phone
        res.phones = list(sorted(extracted_phones)) if extracted_phones else None
        # Ограничиваем размер для экономии места в БД/ответов UI
        res.socials = itp_socials[:200] if itp_socials else None

        logger.info(
            "ITP parsed socials for phone=%s: has_tg=%s, has_vk=%s, has_wa=%s, has_viber=%s, has_tt=%s, tg_username=%s, vk_url=%s, vk_id=%s, tt_username=%s, email=%s, name=%s, phone=%s",
            phone,
            res.has_telegram,
            res.has_vk,
            res.has_whatsapp,
            res.has_viber,
            res.has_tiktok,
            bool(res.telegram_username),
            bool(res.vk_profile_url),
            res.vk_user_id,
            bool(res.tiktok_username),
            bool(res.email),
            bool(res.name),
            bool(res.phone),
        )
        logger.info(
            "ITP observed record fields for phone=%s: %s",
            phone,
            sorted(list(observed_fields))[:40],  # ограничиваем объём
        )

        return res

