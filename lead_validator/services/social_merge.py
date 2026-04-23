"""
Слияние данных мессенджеров из формы (webhook) с результатами API (SocialChecker).

Приоритет идентификаторов: данные API; поля формы добавляются как from_form и в sources.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from lead_validator.services.social_checker import SocialCheckResult

logger = logging.getLogger("lead_validator.social_merge")


def _clean_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def extract_form_messenger_hints(form_data: Optional[dict]) -> Dict[str, str]:
    """
    Извлекает из тела webhook поля telegram, vk, whatsapp, viber, skype (Marquiz и плоские формы).
    Поддерживается вложенность contacts.*.
    """
    if not form_data or not isinstance(form_data, dict):
        return {}
    contacts = form_data.get("contacts") or {}
    if not isinstance(contacts, dict):
        contacts = {}

    keys = ("telegram", "vk", "whatsapp", "viber", "skype")
    out: Dict[str, str] = {}
    for key in keys:
        val = (
            form_data.get(key)
            or form_data.get(key.capitalize())
            or contacts.get(key)
            or contacts.get(key.capitalize())
        )
        s = _clean_str(val)
        if s:
            out[key] = s
    return out


def _hint_implies_account(raw: str) -> bool:
    return bool(raw and raw.strip() and raw.strip().lower() not in ("-", "—", "none", "нет"))


def merge_social_accounts_payload(
    social_result: Optional["SocialCheckResult"],
    form_data: Optional[dict],
):
    """
    Возвращает (merged_dict, bool_overrides) для has_telegram / has_vk / ... при сигнале из формы.
    """
    merged: Dict[str, Any] = {}
    overrides: Dict[str, Optional[bool]] = {}

    if social_result is not None:
        if social_result.has_telegram and social_result.telegram_username:
            merged["telegram"] = {
                "username": social_result.telegram_username,
                "sources": ["api"],
            }
        elif social_result.has_telegram is True:
            merged["telegram"] = {"has_account": True, "sources": ["api"]}

        if social_result.has_vk and social_result.vk_profile_url:
            merged["vk"] = {
                "profile_url": social_result.vk_profile_url,
                "user_id": social_result.vk_user_id,
                "sources": ["api"],
            }
        elif social_result.has_vk is True:
            merged["vk"] = {"has_account": True, "sources": ["api"]}

        if social_result.has_tiktok and social_result.tiktok_username:
            merged["tiktok"] = {
                "username": social_result.tiktok_username,
                "sources": ["api"],
            }

        if social_result.has_whatsapp is True:
            merged["whatsapp"] = {"has_account": True, "sources": ["api"]}
        if social_result.has_viber is True:
            merged["viber"] = {"has_account": True, "sources": ["api"]}

        # Данные InfoTrackPeople для отображения/отладки (не завязаны на форм-флаги)
        if social_result.itp_email:
            merged["itp_email"] = social_result.itp_email
        if social_result.itp_name:
            merged["itp_name"] = social_result.itp_name
        if social_result.itp_phone:
            merged["itp_phone"] = social_result.itp_phone
        if social_result.itp_phones:
            merged["itp_phones"] = social_result.itp_phones
        if social_result.itp_socials:
            merged["itp_socials"] = social_result.itp_socials

    hints = extract_form_messenger_hints(form_data)
    for channel, raw in hints.items():
        if not _hint_implies_account(raw):
            continue
        entry = merged.get(channel)
        if entry is None:
            merged[channel] = {"from_form": raw, "sources": ["form"]}
            if channel in ("telegram", "vk", "whatsapp", "viber", "tiktok"):
                overrides["has_%s" % channel] = True
            continue
        if isinstance(entry, dict):
            entry["from_form"] = raw
            src = entry.setdefault("sources", [])
            if "form" not in src:
                src.append("form")
        if channel in ("telegram", "vk", "whatsapp", "viber", "tiktok"):
            k = "has_%s" % channel
            if k not in overrides:
                overrides[k] = True

    return merged, overrides


def social_payload_to_json(merged: dict) -> Optional[str]:
    if not merged:
        return None
    try:
        return json.dumps(merged, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        logger.warning("social_payload_to_json failed: %s", e)
        return None
