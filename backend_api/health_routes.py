"""
Диагностика SMTP без утечки паролей: статус конфигурации и опциональная TCP-проверка по секрету.
"""

from __future__ import annotations

import asyncio
import logging
import socket
from os import getenv

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend_api.services.auth_mail import is_configured, smtp_delivery_active, smtp_enabled
from core.config import get_config

logger = logging.getLogger("api.health")

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/smtp")
def smtp_status():
    """Публично: только флаги конфигурации (без хоста/логина в ответе)."""
    cfg = get_config()
    host_set = bool((cfg.smtp.host or "").strip())
    from_set = bool((cfg.smtp.from_addr or "").strip())
    return {
        "smtp_enabled": smtp_enabled(),
        "smtp_host_configured": host_set,
        "smtp_from_configured": from_set,
        "smtp_is_configured": is_configured(),
        "smtp_delivery_active": smtp_delivery_active(),
        "smtp_port": cfg.smtp.port,
        "smtp_use_tls": cfg.smtp.use_tls,
        "support_inbox_configured": bool((cfg.support.inbox_email or "").strip()),
        "hints": _status_hints(smtp_enabled(), host_set, from_set, smtp_delivery_active()),
    }


def _status_hints(enabled: bool, host_set: bool, from_set: bool, delivery: bool) -> list[str]:
    hints: list[str] = []
    if not enabled:
        hints.append("SMTP_ENABLED=false — письма не отправляются.")
    elif not host_set:
        hints.append("Задайте SMTP_HOST.")
    elif not from_set:
        hints.append("Задайте SMTP_FROM.")
    elif not delivery:
        hints.append("Почта не готова к отправке: проверьте SMTP_* в .env контейнера backend.")
    else:
        hints.append("Конфигурация SMTP достаточна для попытки отправки; при ошибках смотрите логи и smtp-probe.")
    return hints


class SmtpProbeIn(BaseModel):
    secret: str = Field(..., min_length=1, max_length=256)


@router.post("/smtp-probe")
async def smtp_tcp_probe(body: SmtpProbeIn):
    """
    TCP connect к SMTP_HOST:SMTP_PORT (без STARTTLS/login).
    Защита: в .env задайте SMTP_DIAGNOSE_SECRET и передайте его в теле { "secret": "..." }.
    """
    expected = (getenv("SMTP_DIAGNOSE_SECRET") or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="На сервере не задан SMTP_DIAGNOSE_SECRET — удалённая проверка TCP отключена.",
        )
    if body.secret != expected:
        raise HTTPException(status_code=403, detail="Неверный секрет.")

    cfg = get_config()
    host = (cfg.smtp.host or "").strip()
    port = int(cfg.smtp.port or 587)
    if not host:
        return {"ok": False, "step": "config", "error": "SMTP_HOST пустой"}

    def try_connect():
        s = socket.create_connection((host, port), timeout=10)
        s.close()

    try:
        await asyncio.wait_for(asyncio.to_thread(try_connect), timeout=12)
        return {
            "ok": True,
            "step": "tcp_connect",
            "port": port,
            "message": "TCP-соединение с SMTP установлено (STARTTLS/авторизация не проверялись).",
        }
    except OSError as e:
        logger.warning("smtp-probe TCP failed: %s", e)
        return {
            "ok": False,
            "step": "tcp_connect",
            "errno": e.errno,
            "error": str(e),
            "hint": _errno_hint(e.errno),
        }
    except asyncio.TimeoutError:
        return {
            "ok": False,
            "step": "tcp_connect",
            "error": "timeout",
            "hint": "Таймаут: порт закрыт, фильтр или неверный хост.",
        }


def _errno_hint(errno: int | None) -> str:
    if errno == 101:
        return (
            "Network unreachable — типично для Docker без IPv6 к smtp.yandex.ru (AAAA), "
            "или нет исходящего интернета с контейнера. Проверьте сеть/VPC и при необходимости форсируйте IPv4."
        )
    if errno == 111:
        return "Connection refused — порт закрыт на хосте или неверный SMTP_PORT (587 vs 465)."
    if errno in (110, 10060):
        return "Timeout — файрвол или хост недоступен."
    return "См. errno в ответе и логи контейнера backend."
