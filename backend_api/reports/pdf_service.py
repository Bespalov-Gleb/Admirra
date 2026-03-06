"""
Генерация PDF-отчётов из HTML (WeasyPrint).
"""
import logging
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy.orm import Session

from backend_api.stats_service import StatsService
from core import models

logger = logging.getLogger(__name__)

REPORT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Отчёт за период {{ start_date }} — {{ end_date }}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; color: #333; }
    h1 { font-size: 20px; margin-bottom: 8px; }
    .meta { color: #666; font-size: 12px; margin-bottom: 20px; }
    table { border-collapse: collapse; width: 100%; margin: 16px 0; }
    th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
    th { background: #f5f5f5; font-weight: 600; }
    .kpi { display: flex; flex-wrap: wrap; gap: 16px; margin: 16px 0; }
    .kpi-item { background: #f8f9fa; padding: 12px 16px; border-radius: 8px; min-width: 120px; }
    .kpi-label { font-size: 11px; color: #666; }
    .kpi-value { font-size: 18px; font-weight: 600; }
    .ai-comment-block { background: #e8eef7; border: 1px solid #c5d4ed; padding: 16px; margin: 16px 0; font-size: 13px; line-height: 1.5; white-space: pre-wrap; }
    .section { margin: 24px 0; }
    .section h2 { font-size: 16px; margin-bottom: 8px; }
  </style>
</head>
<body>
  <h1>Отчёт по рекламным кампаниям</h1>
  <div class="meta">Период: {{ start_date }} — {{ end_date }}{% if client_name %} | Проект: {{ client_name }}{% endif %}</div>

  {% if ai_comment %}
  <div class="section">
    <h2>Комментарий ИИ к отчёту</h2>
    <div class="ai-comment-block">{{ ai_comment }}</div>
  </div>
  {% endif %}

  <div class="section">
    <h2>Ключевые показатели</h2>
    <div class="kpi">
      <div class="kpi-item"><div class="kpi-label">Расходы</div><div class="kpi-value">{{ summary.expenses | default(0) | int }} ₽</div></div>
      <div class="kpi-item"><div class="kpi-label">Показы</div><div class="kpi-value">{{ summary.impressions | default(0) | int }}</div></div>
      <div class="kpi-item"><div class="kpi-label">Клики</div><div class="kpi-value">{{ summary.clicks | default(0) | int }}</div></div>
      <div class="kpi-item"><div class="kpi-label">Лиды</div><div class="kpi-value">{{ summary.leads | default(0) | int }}</div></div>
      <div class="kpi-item"><div class="kpi-label">CPC</div><div class="kpi-value">{{ "%.2f" | format(summary.cpc | default(0)) }} ₽</div></div>
      <div class="kpi-item"><div class="kpi-label">CPA</div><div class="kpi-value">{{ "%.2f" | format(summary.cpa | default(0)) }} ₽</div></div>
    </div>
  </div>

  {% if top_campaigns %}
  <div class="section">
    <h2>Топ кампаний по конверсиям</h2>
    <table>
      <thead><tr><th>Кампания</th><th>Лиды</th><th>Расход</th><th>CPA</th></tr></thead>
      <tbody>
        {% for c in top_campaigns %}
        <tr>
          <td>{{ c.name }}</td>
          <td>{{ c.conversions }}</td>
          <td>{{ "%.0f" | format(c.cost) }} ₽</td>
          <td>{{ "%.2f" | format(c.cpa) if c.conversions else 0 }} ₽</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}

  <div class="meta" style="margin-top: 32px;">Сформировано: {{ generated_at }}</div>
</body>
</html>
"""


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

    try:
        from jinja2 import Template
        template = Template(REPORT_HTML_TEMPLATE)
        html = template.render(
            start_date=start_date,
            end_date=end_date,
            client_name=client_name,
            summary=summary,
            top_campaigns=top_campaigns,
            ai_comment=ai_comment,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
    except ImportError:
        # Fallback without Jinja2
        html = f"""
        <html><body>
        <h1>Отчёт за {start_date} — {end_date}</h1>
        <p>Расходы: {summary.get('expenses', 0):,.0f} ₽</p>
        <p>Показы: {summary.get('impressions', 0):,}</p>
        <p>Клики: {summary.get('clicks', 0):,}</p>
        <p>Лиды: {summary.get('leads', 0):,}</p>
        <p>Сформировано: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </body></html>
        """

    try:
        from weasyprint import HTML
        from io import BytesIO
        pdf_bytes = HTML(string=html).write_pdf()
        return pdf_bytes
    except ImportError as e:
        logger.error("WeasyPrint not installed: %s", e)
        raise ImportError("Установите weasyprint: pip install weasyprint")
