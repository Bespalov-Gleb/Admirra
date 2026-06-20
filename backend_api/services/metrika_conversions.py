"""
Серверные офлайн-конверсии Яндекс.Метрики (Центр конверсий, API).

Денежные цели, наступающие без пользователя в браузере (trial_to_paid,
subscription_renewal, фоновые payment_success), нельзя отправить через reachGoal.
Их грузим офлайн-конверсиями: Метрика по ClientID/yclid находит предшествующий
визит (окно 21 день) и атрибутирует выручку рекламному источнику.

Требуется env:
  METRIKA_COUNTER_ID    — ID счётчика (по умолчанию 109911357)
  METRIKA_OFFLINE_TOKEN — OAuth-токен Яндекса с доступом к счётчику (право редактирования).
Поддерживаются legacy-алиасы METRICA_COUNTER_ID / METRICA_OAUTH_TOKEN из старого .env.example.
Без токена/идентификатора загрузка тихо пропускается (не роняет вебхук оплаты).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_METRIKA_API = "https://api-metrika.yandex.net"


def _counter_id() -> str:
    return (
        os.getenv("METRIKA_COUNTER_ID")
        or os.getenv("METRICA_COUNTER_ID")
        or "109911357"
    ).strip()


def _token() -> str:
    return (
        os.getenv("METRIKA_OFFLINE_TOKEN")
        or os.getenv("METRICA_OAUTH_TOKEN")
        or ""
    ).strip()


async def upload_offline_conversion(
    *,
    target: str,
    price: Optional[float] = None,
    currency: str = "RUB",
    client_id: Optional[str] = None,
    yclid: Optional[str] = None,
    when: Optional[datetime] = None,
) -> bool:
    """
    Загрузить одну офлайн-конверсию. Привязка по ClientID (приоритет) либо yclid.
    Возвращает True при успешной загрузке. Никогда не бросает исключений наружу.
    """
    token = _token()
    if not token:
        logger.info("Metrika offline conversion skipped (no METRIKA_OFFLINE_TOKEN): target=%s", target)
        return False

    cid = str(client_id).strip() if client_id else ""
    yc = str(yclid).strip() if yclid else ""
    if not cid and not yc:
        logger.info("Metrika offline conversion skipped (no ClientID/yclid): target=%s", target)
        return False

    ts = int((when or datetime.utcnow()).timestamp())
    if cid:
        id_type, id_col, id_val = "CLIENT_ID", "ClientId", cid
    else:
        id_type, id_col, id_val = "YCLID", "Yclid", yc

    header = [id_col, "Target", "DateTime"]
    row = [id_val, str(target), str(ts)]
    if price is not None:
        try:
            header += ["Price", "Currency"]
            row += [str(round(float(price), 2)), (currency or "RUB")]
        except (TypeError, ValueError):
            pass

    csv_data = ",".join(header) + "\n" + ",".join(row) + "\n"
    url = f"{_METRIKA_API}/management/v1/counter/{_counter_id()}/offline_conversions/upload"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                params={"client_id_type": id_type},
                headers={"Authorization": f"OAuth {token}"},
                files={"file": ("conversions.csv", csv_data, "text/csv")},
            )
        if resp.status_code == 200:
            logger.info("Metrika offline conversion uploaded: target=%s id_type=%s", target, id_type)
            return True
        logger.warning(
            "Metrika offline conversion failed (%s): target=%s %s",
            resp.status_code, target, resp.text[:300],
        )
        return False
    except Exception as err:
        logger.warning("Metrika offline conversion error: target=%s %s", target, err)
        return False
