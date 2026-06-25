"""
Общий рендерер HTML-отчёта. Используется для веб-просмотра и экспорта в PDF/PNG.
Стиль повторяет дашборд GeneralStats3: KPI-карточки 3×2, таблица кампаний
с цветными строками (orange/green/blue), AI-комментарий.
"""

VAT_RATE = 1.22


def _is_avito_platform(value) -> bool:
    return str(value or "").strip().lower() in {"avito", "avito_ads"}


def _campaign_platform(campaign: dict) -> str:
    platform = campaign.get("platform") or campaign.get("channel")
    if platform:
        return str(platform)
    name = str(campaign.get("name") or campaign.get("campaign_name") or "").lower()
    if name.startswith("[avito]") or name.startswith("[авито]"):
        return "avito"
    return ""


def _with_channel_vat(value, platform=None) -> float:
    raw = float(value or 0)
    return raw if _is_avito_platform(platform) else raw * VAT_RATE


def _with_cost_breakdown_vat(value, cost_by_platform: dict | None, platform=None) -> float:
    if isinstance(cost_by_platform, dict):
        return (
            float(cost_by_platform.get("yandex") or 0) * VAT_RATE
            + float(cost_by_platform.get("vk") or 0) * VAT_RATE
            + float(cost_by_platform.get("avito") or 0)
        )
    return _with_channel_vat(value, platform)


def _summary_platform(data: dict, campaigns: list) -> str:
    platform = data.get("platform") or data.get("channel")
    if platform:
        return str(platform)
    if campaigns and all(_is_avito_platform(_campaign_platform(c)) for c in campaigns):
        return "avito"
    return ""


def _escape_html(text: str) -> str:
    if not text:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _fmt(value, decimals=0) -> str:
    if decimals == 0:
        return f"{int(value):,}".replace(",", " ")
    return f"{value:,.{decimals}f}".replace(",", " ")


_KPI_ICONS = {
    "expenses": (
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3464F3" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 12V7H5a2 2 0 010-4h14v4"/><path d="M3 5v14a2 2 0 002 2h16v-5"/>'
        '<path d="M18 12a2 2 0 000 4h4v-4h-4z"/></svg>'
    ),
    "impressions": (
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F0926D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg>'
    ),
    "clicks": (
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M9 2L9 13L13.5 9.5L16.5 18.5L18.5 17.5L15.5 8.5L21 8.5L9 2Z"/></svg>'
    ),
    "cpc": (
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#D38CFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg>'
    ),
    "leads": (
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#8ADA70" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/>'
        '<line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'
    ),
    "cpa": (
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#EB8525" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>'
    ),
}

_KPI_COLORS = {
    "expenses": "#3464F3",
    "impressions": "#F0926D",
    "clicks": "#38BDF8",
    "cpc": "#D38CFF",
    "leads": "#8ADA70",
    "cpa": "#EB8525",
}

_ROW_TINTS = ["orange", "green", "blue"]
_ROW_BACKGROUNDS = {"orange": "#fff4ee", "green": "#eafcf0", "blue": "#e8eefc"}


def _kpi_card(key: str, label: str, value: str, subtitle: str = "") -> str:
    icon = _KPI_ICONS.get(key, "")
    color = _KPI_COLORS.get(key, "#3464F3")
    return f"""<div class="kpi-card">
      <div class="kpi-icon" style="background:{color}14;">{icon}</div>
      <div class="kpi-body">
        <span class="kpi-label">{label}</span>
        <span class="kpi-value">{value}</span>
      </div>
    </div>"""


def render_report_html(data: dict) -> str:
    s = data.get("summary", {})
    tc = data.get("top_campaigns", [])
    client_name = data.get("client_name", "")
    ai_comment = data.get("ai_comment", "")
    start_date = data.get("start_date", "")
    end_date = data.get("end_date", "")
    generated_at = data.get("generated_at", "")

    summary_platform = _summary_platform(data, tc)

    expenses = _with_cost_breakdown_vat(s.get("expenses", 0), s.get("cost_by_platform"), summary_platform)
    impressions = int(s.get("impressions", 0))
    clicks = int(s.get("clicks", 0))
    leads = int(s.get("leads", 0))
    cpc = expenses / clicks if clicks > 0 else _with_channel_vat(s.get("cpc", 0), summary_platform)
    cpa = expenses / leads if leads > 0 else _with_channel_vat(s.get("cpa", 0), summary_platform)

    kpi_html = "".join([
        _kpi_card("expenses", "Расходы", f"{_fmt(expenses)} ₽", "За период"),
        _kpi_card("impressions", "Показы", _fmt(impressions), "По всем каналам"),
        _kpi_card("clicks", "Клики", _fmt(clicks), "Все переходы"),
        _kpi_card("cpc", "CPC", f"{_fmt(cpc, 2)} ₽", "Стоимость клика"),
        _kpi_card("leads", "Лиды", f"{_fmt(leads)} шт.", "По всем каналам"),
        _kpi_card("cpa", "CPL", f"{_fmt(cpa, 2)} ₽", "Стоимость лида"),
    ])

    campaigns_rows = ""
    for i, c in enumerate(tc[:10]):
        name = _escape_html(c.get("name", c.get("campaign_name", "—")))
        c_platform = _campaign_platform(c)
        conv = int(c.get("conversions", 0))
        cost = _fmt(_with_channel_vat(c.get("cost", 0), c_platform))
        impr = _fmt(int(c.get("impressions", 0)))
        clk = _fmt(int(c.get("clicks", 0)))
        c_cpc = _fmt(_with_channel_vat(c.get("cpc", 0), c_platform), 2)
        c_cpa = _fmt(_with_channel_vat(c.get("cpa", 0), c_platform), 2) if conv else "—"
        tint = _ROW_TINTS[i % len(_ROW_TINTS)]
        bg = _ROW_BACKGROUNDS[tint]
        campaigns_rows += (
            f'<tr style="background:{bg};">'
            f"<td>{name}</td>"
            f'<td class="num">{cost} ₽</td>'
            f'<td class="num">{impr}</td>'
            f'<td class="num">{clk}</td>'
            f'<td class="num">{c_cpc} ₽</td>'
            f'<td class="num">{conv} шт.</td>'
            f'<td class="num">{c_cpa}{" ₽" if conv else ""}</td>'
            f"</tr>"
        )

    campaigns_html = ""
    if tc:
        campaigns_html = f"""
    <div class="panel campaigns-panel">
      <h2>Лучшие рекламные кампании</h2>
      <table>
        <thead><tr>
          <th>Название кампании</th>
          <th class="num">Расход</th>
          <th class="num">Показы</th>
          <th class="num">Клики</th>
          <th class="num">CPC</th>
          <th class="num">Лиды</th>
          <th class="num">CPL</th>
        </tr></thead>
        <tbody>{campaigns_rows}</tbody>
      </table>
    </div>"""

    comment_html = ""
    if ai_comment:
        escaped = _escape_html(ai_comment).replace("\n", "<br>")
        comment_html = f"""
    <div class="panel ai-panel">
      <h2>Комментарий ИИ к отчёту</h2>
      <div class="ai-block">{escaped}</div>
    </div>"""

    project_line = f'<div class="header-project">{_escape_html(client_name)}</div>' if client_name else ""

    # Опциональный блок «Динамика по месяцам» (Phase 3 — opt-in, помесячно).
    dynamics_html = ""
    dyn_periods = (data.get("dynamics") or {}).get("periods") or []
    if dyn_periods:
        points = []
        has_incomplete = False
        for p in dyn_periods:
            cost = _with_cost_breakdown_vat(p.get("cost", 0), p.get("cost_by_platform"))
            leads = int(p.get("leads", 0) or 0)
            cpl = cost / leads if leads > 0 else 0
            incomplete = bool(p.get("incomplete"))
            if incomplete:
                has_incomplete = True
            points.append({
                "label": _escape_html(p.get("label", "")),
                "cost": cost,
                "leads": leads,
                "cpl": cpl,
                "incomplete": incomplete,
            })

        chart_w, chart_h = 820, 235
        pad_l, pad_r, pad_t, pad_b = 42, 22, 18, 70
        plot_w = chart_w - pad_l - pad_r
        plot_h = chart_h - pad_t - pad_b
        max_cost = max([pt["cost"] for pt in points] + [1])
        step = plot_w / max(len(points), 1)
        bar_w = min(70, step * 0.55)
        bars = ""
        for i, pt in enumerate(points):
            h = max(4, pt["cost"] / max_cost * plot_h)
            x = pad_l + i * step + (step - bar_w) / 2
            y = pad_t + plot_h - h
            fill = "#3464F3" if not pt["incomplete"] else "#9DB7FF"
            dash = ' stroke="#3464F3" stroke-dasharray="4 4"' if pt["incomplete"] else ""
            bars += (
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="8" fill="{fill}"{dash}/>'
                f'<text x="{x + bar_w / 2:.1f}" y="{pad_t + plot_h + 22}" text-anchor="middle" font-size="11" fill="#64748b">{pt["label"]}</text>'
                f'<text x="{x + bar_w / 2:.1f}" y="{pad_t + plot_h + 39}" text-anchor="middle" font-size="10" fill="#94a3b8">{pt["leads"]} лид.</text>'
                f'<text x="{x + bar_w / 2:.1f}" y="{pad_t + plot_h + 55}" text-anchor="middle" font-size="10" fill="#94a3b8">CPL {_fmt(pt["cpl"], 0)} ₽</text>'
            )
        note = (
            '<div style="font-size:11px;color:#94a3b8;margin-top:8px;">* — текущий период ещё не завершён</div>'
            if has_incomplete else ""
        )
        dynamics_html = f"""
    <div class="panel campaigns-panel">
      <h2>Динамика по месяцам</h2>
      <svg width="100%" viewBox="0 0 {chart_w} {chart_h}" role="img" aria-label="Тренд динамики по месяцам">
        <rect x="0" y="0" width="{chart_w}" height="{chart_h}" rx="18" fill="#f8fafc"/>
        <line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{chart_w - pad_r}" y2="{pad_t + plot_h}" stroke="#e2e8f0"/>
        {bars}
      </svg>
      <div style="display:flex;gap:12px;align-items:center;margin-top:10px;color:#64748b;font-size:12px;">
        <span style="display:inline-flex;width:10px;height:10px;border-radius:4px;background:#3464F3;"></span>
        <span>Столбцы показывают расход, подписи — лиды и CPL по периоду.</span>
      </div>
      {note}
    </div>"""

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
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: #f3f4f8;
      color: #09183F;
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
      padding: 24px;
    }}
    .dashboard {{
      max-width: 960px;
      margin: 0 auto;
    }}

    /* Header */
    .header {{
      background: linear-gradient(135deg, #2563EB 0%, #1d4ed8 50%, #1e40af 100%);
      color: #fff;
      padding: 24px 28px;
      border-radius: 16px;
      box-shadow: 0 4px 14px rgba(37,99,235,0.25);
      margin-bottom: 24px;
    }}
    .header h1 {{
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.02em;
      margin-bottom: 6px;
    }}
    .header-period {{
      font-size: 15px;
      font-weight: 600;
      opacity: 0.95;
    }}
    .header-project {{
      font-size: 13px;
      opacity: 0.85;
      margin-top: 4px;
    }}

    /* KPI Grid — matches dashboard 3-column layout */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      margin-bottom: 24px;
    }}
    .kpi-card {{
      background: #fff;
      border-radius: 16px;
      padding: 20px;
      display: flex;
      align-items: center;
      gap: 14px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    .kpi-icon {{
      width: 40px;
      height: 40px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }}
    .kpi-body {{
      display: flex;
      flex-direction: column;
    }}
    .kpi-label {{
      font-size: 11px;
      color: #64748b;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .kpi-value {{
      font-size: 20px;
      font-weight: 700;
      color: #09183F;
      letter-spacing: -0.02em;
      margin-top: 2px;
    }}

    /* Panels */
    .panel {{
      background: #fff;
      border-radius: 16px;
      padding: 24px 28px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      margin-bottom: 20px;
    }}
    .panel h2 {{
      font-size: 16px;
      font-weight: 600;
      color: #09183F;
      margin-bottom: 20px;
    }}

    /* Campaign table — colored rows like dashboard */
    .campaigns-panel table {{
      border-collapse: separate;
      border-spacing: 0 10px;
      width: 100%;
    }}
    .campaigns-panel th {{
      font-size: 12px;
      color: #b3b3b3;
      font-weight: 500;
      text-transform: none;
      padding: 0 16px 4px;
      border: none;
      background: transparent;
    }}
    .campaigns-panel td {{
      padding: 14px 16px;
      font-size: 13px;
      color: #4b4b4b;
      border: none;
    }}
    .campaigns-panel tr td:first-child {{
      border-radius: 10px 0 0 10px;
      font-weight: 500;
    }}
    .campaigns-panel tr td:last-child {{
      border-radius: 0 10px 10px 0;
    }}
    .num {{
      text-align: right;
    }}
    th.num {{
      text-align: right;
    }}

    /* AI comment */
    .ai-panel .ai-block {{
      background: linear-gradient(145deg, #eff6ff, #dbeafe);
      border: 1px solid #93c5fd;
      padding: 20px 22px;
      border-radius: 12px;
      font-size: 14px;
      line-height: 1.7;
      white-space: pre-wrap;
      color: #1e3a5f;
    }}

    /* Footer */
    .report-footer {{
      text-align: center;
      padding: 16px;
      font-size: 12px;
      color: #94a3b8;
      font-weight: 500;
    }}
    .report-footer .brand {{
      margin-top: 4px;
      font-size: 11px;
      color: #cbd5e1;
    }}
  </style>
</head>
<body>
  <div class="dashboard">
    <div class="header">
      <h1>Отчёт по рекламным кампаниям</h1>
      <div class="header-period">{start_date} — {end_date}</div>
      {project_line}
    </div>

    <section class="kpi-grid">
      {kpi_html}
    </section>

    {comment_html}
    {campaigns_html}
    {dynamics_html}

    <div class="report-footer">
      Сформировано {generated_at}
      <div class="brand">AdMirra — аналитика рекламных кампаний</div>
    </div>
  </div>
</body>
</html>"""
