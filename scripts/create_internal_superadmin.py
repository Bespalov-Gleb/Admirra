"""Разовое приглашение первого Super Admin без изменения runtime-логики админки.

Запуск в контейнере:
    docker compose run --rm backend python scripts/create_internal_superadmin.py \
      --email owner@example.com --first-name Имя --last-name Фамилия

Команда печатает одноразовую invite-ссылку. Пароль задаётся владельцем в браузере.
"""
from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Пригласить первого внутреннего Super Admin")
    parser.add_argument("--email", required=True)
    parser.add_argument("--first-name", default="")
    parser.add_argument("--last-name", default="")
    parser.add_argument("--base-url", default="https://admin.admirra.ru")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    from core import models, security
    from core.database import SessionLocal
    from backend_api.auth_helpers import hash_verification_token, verification_expiry

    email = args.email.strip().lower()

    db = SessionLocal()
    try:
        existing = db.query(models.User).filter(models.User.email == email).first()
        if existing:
            if existing.role in {models.UserRole.ADMIN, models.UserRole.SUPERADMIN} and existing.staff_status == models.StaffStatus.ACTIVE:
                print(f"Super Admin уже существует: {email}")
                return 0
            if existing.role not in {models.UserRole.ADMIN, models.UserRole.SUPERADMIN}:
                print(
                    "Ошибка: email уже принадлежит клиентскому или другому staff-аккаунту. "
                    "Используйте отдельный рабочий email.",
                    file=sys.stderr,
                )
                return 3
            user = existing
        else:
            user = models.User(
                email=email,
                username=email.split("@", 1)[0],
                first_name=args.first_name.strip() or None,
                last_name=args.last_name.strip() or None,
                password_hash=security.get_password_hash(secrets.token_urlsafe(24)),
                role=models.UserRole.SUPERADMIN,
                staff_status=models.StaffStatus.PENDING,
                is_active=True,
                email_verified=False,
            )
            db.add(user)

        raw_token = secrets.token_urlsafe(32)
        user.email_verification_token_hash = hash_verification_token(raw_token)
        user.email_verification_expires_at = verification_expiry(7 * 24)
        db.commit()
        db.refresh(user)
        invite_url = f"{args.base_url.rstrip('/')}/invite/{raw_token}"
        print(f"Приглашение Super Admin создано: {user.email} ({user.id})")
        print(f"Ссылка действует 7 дней: {invite_url}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
