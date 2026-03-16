"""
Генерация PDF-отчётов из HTML (WeasyPrint).
Использует общий рендерер report_html для единообразия с веб-просмотром.
"""
import logging
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy.orm import Session

from backend_api.reports.report_html import render_report_html
from backend_api.stats_service import StatsService
from core import models

logger = logging.getLogger(__name__)


def generate_report_pdf(
    db: Session,
    user_id: uuid.UUID,
    client_id: Optional[uuid.UUID],
    start_date: str,
    end_date: str,
    comment: Optional[str] = None,
) -> bytes:
    """
    Генерирует PDF-отчёт на основе данных дашборда.
    """
    effective_client_ids = StatsService.get_effective_client_ids(db, user_id, client_id)
    if not effective_client_ids:
        raise ValueError("Нет доступа к данным")

    try:
        from datetime import datetime as dt
        d_end = dt.strptime(end_date, "%Y-%m-%d").date()
        d_start = dt.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Неверный формат дат. Используйте YYYY-MM-DD.")

    summary = StatsService.aggregate_summary(
        db, effective_client_ids, d_start, d_end, "all", None, None
    )
    campaigns = StatsService.get_campaign_stats(
        db, effective_client_ids, d_start, d_end, "all", None, None
    )
    top_campaigns = sorted(
        [c for c in campaigns if c.get("conversions", 0) > 0],
        key=lambda x: x.get("conversions", 0),
        reverse=True,
    )[:10]

    client_name = None
    if client_id and len(effective_client_ids) == 1:
        client = db.query(models.Client).filter_by(id=client_id).first()
        if client:
            client_name = client.name

    ai_comment = (comment or "").strip() if comment else ""
    logger.info("pdf_service: rendering PDF, ai_comment length=%d", len(ai_comment))

    data = {
        "summary": summary,
        "top_campaigns": top_campaigns,
        "client_name": client_name or "",
        "ai_comment": ai_comment,
        "start_date": start_date,
        "end_date": end_date,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    html = render_report_html(data)

    try:
        from weasyprint import HTML
        from io import BytesIO
        pdf_bytes = HTML(string=html).write_pdf()
        return pdf_bytes
    except ImportError as e:
        logger.error("WeasyPrint not installed: %s", e)
        raise ImportError("Установите weasyprint: pip install weasyprint")
