"""Стартовые данные internal_admin (SEO-страницы)."""
from sqlalchemy.orm import Session

from internal_admin.models import SeoSitePage

DEFAULT_SITE_PAGES: list[tuple[str, str]] = [
    ("/", "Главная"),
    ("/prices", "Тарифы"),
    ("/blog", "Блог"),
    ("/contacts", "Контакты"),
    ("/privacy", "Политика конфиденциальности"),
    ("/terms", "Пользовательское соглашение"),
]


def ensure_default_seo_pages(db: Session) -> None:
    for path, title in DEFAULT_SITE_PAGES:
        exists = db.query(SeoSitePage).filter(SeoSitePage.path == path).first()
        if exists:
            continue
        db.add(SeoSitePage(path=path, title=title))
    db.commit()
