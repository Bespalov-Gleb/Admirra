"""
Генерация PDF-отчётов из HTML (WeasyPrint).
Использует общий рендерер report_html для единообразия с веб-просмотром.
"""
import logging
from datetime import datetime, date
from typing import Optional
import uuid

from sqlalchemy.orm import Session

from backend_api.reports.report_html import render_report_html
from backend_api.stats_service import StatsService
from core import models

logger = logging.getLogger(__name__)


def _daily_series(db: Session, client_ids, d_start, d_end, platform: str = "all"):
    """Дневная серия (расход/клики/лиды) для главного графика отчёта.
    Расход отдаём с разбивкой по платформам — НДС применяет рендерер."""
    from sqlalchemy import func as sa_func
    out = {}

    def add(rows, key):
        for stat_date, cost, clicks, leads, impressions in rows:
            item = out.setdefault(str(stat_date), {"cost_yandex": 0.0, "cost_vk": 0.0, "cost_avito": 0.0, "clicks": 0, "leads": 0, "impressions": 0})
            item[f"cost_{key}"] += float(cost or 0)
            item["clicks"] += int(clicks or 0)
            item["leads"] += int(leads or 0)
            item["impressions"] += int(impressions or 0)

    if platform in ("all", "yandex"):
        add(
            db.query(models.YandexStats.date, sa_func.sum(models.YandexStats.cost), sa_func.sum(models.YandexStats.clicks), sa_func.sum(models.YandexStats.conversions), sa_func.sum(models.YandexStats.impressions))
            .filter(models.YandexStats.client_id.in_(client_ids), models.YandexStats.date >= d_start, models.YandexStats.date <= d_end)
            .group_by(models.YandexStats.date).all(),
            "yandex",
        )
    if platform in ("all", "vk"):
        add(
            db.query(models.VKStats.date, sa_func.sum(models.VKStats.cost), sa_func.sum(models.VKStats.clicks), sa_func.sum(models.VKStats.conversions), sa_func.sum(models.VKStats.impressions))
            .filter(models.VKStats.client_id.in_(client_ids), models.VKStats.date >= d_start, models.VKStats.date <= d_end)
            .group_by(models.VKStats.date).all(),
            "vk",
        )
    if platform in ("all", "avito"):
        add(
            db.query(models.AvitoStats.date, sa_func.sum(models.AvitoStats.cost), sa_func.sum(models.AvitoStats.clicks), sa_func.sum(models.AvitoStats.conversions), sa_func.sum(models.AvitoStats.impressions))
            .filter(models.AvitoStats.client_id.in_(client_ids), models.AvitoStats.date >= d_start, models.AvitoStats.date <= d_end)
            .group_by(models.AvitoStats.date).all(),
            "avito",
        )
    return [{"date": d, **vals} for d, vals in sorted(out.items())]


def generate_report_pdf(
    db: Session,
    user_id: uuid.UUID,
    client_id: Optional[uuid.UUID],
    start_date: str,
    end_date: str,
    comment: Optional[str] = None,
    include_dynamics: bool = False,
    folder_id: Optional[str] = None,
    platform: str = "all",
    layout: str = "desktop",
    sections: list | None = None,
    chart_metrics: list | None = None,
    dynamics_metrics: list | None = None,
) -> bytes:
    """
    Генерирует PDF-отчёт на основе данных дашборда.
    folder_id — скоуп «папка»: сводный отчёт по всем вложенным проектам.
    """
    if folder_id and not client_id:
        effective_client_ids = StatsService.resolve_folder_client_ids(db, user_id, folder_id)
    else:
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
        db, effective_client_ids, d_start, d_end, platform or "all", None, None
    )
    campaigns = StatsService.get_campaign_stats(
        db, effective_client_ids, d_start, d_end, platform or "all", None, None
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
    elif folder_id:
        try:
            folder = db.query(models.Folder).filter_by(id=uuid.UUID(str(folder_id))).first()
            if folder:
                n_projects = len(effective_client_ids)
                word = "проекту" if n_projects % 10 == 1 and n_projects % 100 != 11 else "проектам"
                client_name = f"Папка «{folder.name}» · сводный отчёт по {n_projects} {word}"
        except (ValueError, TypeError):
            pass

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
        "platform": platform or "all",
        "layout": layout or "desktop",
        "sections": sections or ["kpi", "chart", "channels", "campaigns"],
        "chart_metrics": chart_metrics or ["cost", "clicks"],
        "dynamics_metrics": dynamics_metrics or ["cost"],
    }

    # Дневная серия для главного графика (как на дашборде) — прямой запрос к витрине
    if "chart" in data["sections"]:
        try:
            data["daily"] = _daily_series(db, effective_client_ids, d_start, d_end, platform or "all")
        except Exception as e:
            logger.warning("Daily series skipped: %s", e)

    # Разбивка по рекламным каналам (блок «Каналы» как канальные карточки дашборда)
    if (platform or "all") == "all" and "channels" in data["sections"]:
        try:
            channels_breakdown = []
            for ch in ("yandex", "vk", "avito"):
                ch_summary = StatsService.aggregate_summary(db, effective_client_ids, d_start, d_end, ch, None, None)
                if any(float(ch_summary.get(k) or 0) for k in ("expenses", "impressions", "clicks", "leads")):
                    channels_breakdown.append({"code": ch, **ch_summary})
            data["channels"] = channels_breakdown
        except Exception as e:
            logger.warning("Channels breakdown skipped: %s", e)

    # Опциональный блок «Динамика по месяцам» (трейлинг 6 календарных месяцев до end_date).
    if include_dynamics:
        try:
            from backend_api.services.dynamics_service import get_dynamics_series
            total = d_end.year * 12 + (d_end.month - 1) - 5
            y2, m2 = divmod(total, 12)
            dyn_from = date(y2, m2 + 1, 1)
            data["dynamics"] = get_dynamics_series(
                db, effective_client_ids, dyn_from, d_end, "all", None, "month"
            )
        except Exception as e:
            logger.warning("Dynamics block skipped: %s", e)

    html = render_report_html(data, layout=layout or "desktop")

    try:
        from weasyprint import HTML
        from io import BytesIO
        pdf_bytes = HTML(string=html).write_pdf()
        return pdf_bytes
    except ImportError as e:
        logger.error("WeasyPrint not installed: %s", e)
        raise ImportError("Установите weasyprint: pip install weasyprint")
