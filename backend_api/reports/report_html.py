"""
Общий рендерер HTML-отчёта. Используется для веб-просмотра и экспорта в PDF/PNG.
"""

VAT_RATE = 1.22


def _with_vat(value) -> float:
    return float(value or 0) * VAT_RATE


def _escape_html(text: str) -> str:
    """Экранирует HTML для безопасного вывода."""
    if not text:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_report_html(data: dict) -> str:
    """Рендерит HTML-страницу отчёта."""
    s = data.get("summary", {})
    tc = data.get("top_campaigns", [])
    client_name = data.get("client_name", "")
    ai_comment = data.get("ai_comment", "")
    start_date = data.get("start_date", "")
    end_date = data.get("end_date", "")
    generated_at = data.get("generated_at", "")

    kpi_html = f"""
    <div class="kpi">
      <div class="kpi-item"><span class="kpi-label">Расходы</span><span class="kpi-value">{int(_with_vat(s.get('expenses', 0))):,} ₽</span></div>
      <div class="kpi-item"><span class="kpi-label">Показы</span><span class="kpi-value">{int(s.get('impressions', 0)):,}</span></div>
      <div class="kpi-item"><span class="kpi-label">Клики</span><span class="kpi-value">{int(s.get('clicks', 0)):,}</span></div>
      <div class="kpi-item"><span class="kpi-label">Лиды</span><span class="kpi-value">{int(s.get('leads', 0)):,}</span></div>
      <div class="kpi-item"><span class="kpi-label">CPC</span><span class="kpi-value">{_with_vat(s.get('cpc', 0)):.2f} ₽</span></div>
      <div class="kpi-item"><span class="kpi-label">CPA</span><span class="kpi-value">{_with_vat(s.get('cpa', 0)):.2f} ₽</span></div>
    </div>
    """

    campaigns_rows = ""
    for c in tc:
        name = _escape_html(c.get("name", c.get("campaign_name", "—")))
        conv = c.get("conversions", 0)
        cost = f"{_with_vat(c.get('cost', 0)):,.0f} ₽"
        cpa = f"{_with_vat(c.get('cpa', 0)):.2f} ₽" if c.get("conversions") else "—"
        campaigns_rows += f"<tr><td>{name}</td><td>{conv}</td><td>{cost}</td><td>{cpa}</td></tr>"

    campaigns_html = ""
    if tc:
        campaigns_html = f"""
    <div class="section">
      <h2>Топ кампаний по конверсиям</h2>
      <table>
        <thead><tr><th>Кампания</th><th>Лиды</th><th>Расход</th><th>CPA</th></tr></thead>
        <tbody>{campaigns_rows}</tbody>
      </table>
    </div>
    """

    comment_html = ""
    if ai_comment:
        escaped = _escape_html(ai_comment).replace("\n", "<br>")
        comment_html = f"""
    <div class="section">
      <h2>Комментарий ИИ к отчёту</h2>
      <div class="ai-comment-block">{escaped}</div>
    </div>
    """

    project_div = f'<div class="project">Проект: {_escape_html(client_name)}</div>' if client_name else ""

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Отчёт за период {start_date} — {end_date}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 0; color: #09183F; background: #f1f5f9; line-height: 1.6; -webkit-font-smoothing: antialiased; }}
    .page {{ max-width: 820px; margin: 0 auto; min-height: 100vh; display: flex; flex-direction: column; }}
    .banner {{ background: linear-gradient(135deg, #2563EB 0%, #1d4ed8 50%, #1e40af 100%); color: #fff; padding: 24px 28px; border-radius: 0 0 16px 16px; box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25); }}
    .banner h1 {{ margin: 0 0 8px; font-size: 20px; font-weight: 700; letter-spacing: -0.02em; }}
    .banner .period {{ font-size: 15px; font-weight: 600; margin: 4px 0 0; opacity: 0.95; }}
    .banner .project {{ font-size: 13px; opacity: 0.85; margin-top: 6px; }}
    .content {{ flex: 1; background: #fff; margin: 0 16px; padding: 28px 32px; border-radius: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); margin-bottom: 24px; }}
    .section {{ margin: 28px 0; }}
    .section:first-child {{ margin-top: 0; }}
    .section h2 {{ font-size: 15px; font-weight: 600; color: #2563EB; margin: 0 0 16px; letter-spacing: -0.01em; text-transform: uppercase; font-size: 12px; letter-spacing: 0.08em; }}
    .kpi {{ display: flex; flex-wrap: wrap; gap: 14px; margin: 0; }}
    .kpi-item {{ background: linear-gradient(145deg, #f8fafc, #f1f5f9); border: 1px solid #e2e8f0; padding: 16px 18px; border-radius: 12px; min-width: 130px; transition: box-shadow 0.2s; }}
    .kpi-item:hover {{ box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08); }}
    .kpi-label {{ display: block; font-size: 11px; color: #64748b; font-weight: 500; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px; }}
    .kpi-value {{ font-size: 20px; font-weight: 700; color: #09183F; letter-spacing: -0.02em; }}
    table {{ border-collapse: separate; border-spacing: 0; width: 100%; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
    th, td {{ padding: 14px 16px; text-align: left; border: none; }}
    th {{ background: #f8fafc; font-weight: 600; font-size: 12px; color: #475569; text-transform: uppercase; letter-spacing: 0.04em; }}
    tr:nth-child(even) {{ background: #fafbfc; }}
    tr:nth-child(odd) {{ background: #fff; }}
    tr:hover td {{ background: #f1f5f9 !important; }}
    td {{ font-size: 14px; color: #334155; }}
    .ai-comment-block {{ background: linear-gradient(145deg, #eff6ff, #dbeafe); border: 1px solid #93c5fd; padding: 20px 22px; border-radius: 12px; font-size: 14px; line-height: 1.65; white-space: pre-wrap; color: #1e3a5f; }}
    .footer {{ text-align: center; padding: 20px 16px; font-size: 12px; color: #94a3b8; font-weight: 500; }}
  </style>
</head>
<body>
  <div class="page">
    <div class="banner">
      <h1>Отчёт по рекламным кампаниям</h1>
      <div class="period">{start_date} — {end_date}</div>
      {project_div}
    </div>
    <div class="content">
      {comment_html}
      <div class="section">
        <h2>Ключевые показатели</h2>
        {kpi_html}
      </div>
      {campaigns_html}
    </div>
    <div class="footer">Сформировано {generated_at}</div>
  </div>
</body>
</html>
"""
