"""Логирование AI usage для internal_admin (тонкая связь с основным приложением)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from internal_admin.services import log_ai_usage, estimate_tokens_from_text


def record_ai_call(
    db: Session,
    *,
    user_id: Optional[UUID],
    action: str,
    prompt_text: str = "",
    response_text: str = "",
    meta: Optional[dict] = None,
) -> None:
    try:
        tin = estimate_tokens_from_text(prompt_text)
        tout = estimate_tokens_from_text(response_text)
        log_ai_usage(
            db,
            user_id=user_id,
            action=action,
            tokens_input=tin,
            tokens_output=tout,
            meta=meta,
        )
    except Exception:
        pass
