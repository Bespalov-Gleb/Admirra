"""
Общий рендерер HTML-отчёта. Используется для веб-просмотра и экспорта в PDF/PNG
(WeasyPrint: HTML+CSS без JS, поэтому вся вёрстка — на таблицах/inline-block,
CSS Grid WeasyPrint НЕ поддерживает; графики — статический SVG).

Вёрстка повторяет дашборд GeneralStats3: KPI-карточки с иконками и трендами,
главный график «Расходы и клики по дням», блок «Каналы», таблица кампаний
с цветными строками, опциональная «Динамика по месяцам», AI-комментарий.

layout: desktop (широкая страница) | mobile (узкая, одна колонка).
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
    if platform and str(platform) != "all":
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


def _fmt_compact(value) -> str:
    n = float(value or 0)
    a = abs(n)
    if a >= 1_000_000:
        return f"{n / 1_000_000:.1f} млн".replace(".", ",")
    if a >= 1000:
        return f"{n / 1000:.0f}к"
    return _fmt(n)


_KPI_ICONS = {
    "expenses": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3464F3" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 12V7H5a2 2 0 010-4h14v4"/><path d="M3 5v14a2 2 0 002 2h16v-5"/>'
        '<path d="M18 12a2 2 0 000 4h4v-4h-4z"/></svg>'
    ),
    "impressions": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F0926D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg>'
    ),
    "clicks": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M9 2L9 13L13.5 9.5L16.5 18.5L18.5 17.5L15.5 8.5L21 8.5L9 2Z"/></svg>'
    ),
    "cpc": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#D38CFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg>'
    ),
    "leads": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#8ADA70" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/>'
        '<line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'
    ),
    "cpa": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#EB8525" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
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

# Для CPC/CPL рост — плохо (красный), для остальных рост — хорошо (зелёный)
_COST_TREND_KEYS = {"cpc", "cpa"}

_ROW_TINTS = ["orange", "green", "blue"]
_ROW_BACKGROUNDS = {"orange": "#fff4ee", "green": "#eafcf0", "blue": "#e8eefc"}

_CHANNEL_META = {
    "yandex": {"name": "Яндекс Директ", "color": "#e5ad00", "soft": "#fff8e7", "short": "Я"},
    "vk": {"name": "VK Реклама", "color": "#2563eb", "soft": "#f3f7ff", "short": "VK"},
    "avito": {"name": "Avito Ads", "color": "#00a871", "soft": "#ecfdf5", "short": "A"},
}


def _trend_badge(trends: dict | None, key: str) -> str:
    if not isinstance(trends, dict) or trends.get(key) is None:
        return ""
    try:
        value = float(trends.get(key) or 0)
    except (TypeError, ValueError):
        return ""
    up = value >= 0
    bad = (up and key in _COST_TREND_KEYS) or (not up and key not in _COST_TREND_KEYS)
    color = "#dc2626" if bad else "#059669"
    bg = "#fee2e2" if bad else "#d1fae5"
    arrow = "▲" if up else "▼"
    sign = "+" if up else ""
    return (
        f'<span style="display:inline-block;padding:2px 7px;border-radius:99px;background:{bg};'
        f'color:{color};font-size:10px;font-weight:700;">{arrow} {sign}{value:.1f}%</span>'
    )


def _kpi_card(key: str, label: str, value: str, subtitle: str, trends: dict | None) -> str:
    icon = _KPI_ICONS.get(key, "")
    color = _KPI_COLORS.get(key, "#3464F3")
    badge = _trend_badge(trends, key)
    return f"""<div class="kpi-card">
      <table class="kpi-inner"><tr>
        <td class="kpi-icon-cell"><div class="kpi-icon" style="background:{color}14;">{icon}</div></td>
        <td>
          <div class="kpi-label">{label}</div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-sub">{subtitle} {badge}</div>
        </td>
      </tr></table>
    </div>"""


# Те же 6 показателей, что на графике дашборда (цвета совпадают с дашбордом)
_CHART_METRIC_META = {
    "cost": {"label": "Расход", "unit": " ₽", "color": "#2563eb", "decimals": 0},
    "impressions": {"label": "Показы", "unit": "", "color": "#F0926D", "decimals": 0},
    "clicks": {"label": "Клики", "unit": "", "color": "#38BDF8", "decimals": 0},
    "cpc": {"label": "CPC", "unit": " ₽", "color": "#D38CFF", "decimals": 2},
    "cpa": {"label": "CPL", "unit": " ₽", "color": "#EB8525", "decimals": 2},
    "leads": {"label": "Конверсии", "unit": "", "color": "#8ADA70", "decimals": 0},
}


def _metric_value_from(item: dict) -> dict:
    """Значения всех 6 метрик из строки daily/period (cost уже с НДС)."""
    cost = float(item.get("cost") or 0)
    clicks = int(item.get("clicks") or 0)
    impressions = int(item.get("impressions") or 0)
    leads = int(item.get("leads") or 0)
    return {
        "cost": cost,
        "impressions": impressions,
        "clicks": clicks,
        "cpc": (cost / clicks) if clicks > 0 else 0.0,
        "cpa": (cost / leads) if leads > 0 else 0.0,
        "leads": leads,
    }


def _single_metric_chart(points: list, metric: str, layout: str, x_labels: list, title_suffix: str) -> str:
    """Один график = одна метрика: область + линия, ось Y слева со значениями,
    подписи дат снизу, точные значения над точками (когда точек немного)."""
    meta = _CHART_METRIC_META[metric]
    width = 900 if layout == "desktop" else 420
    height = 230 if layout == "desktop" else 190
    pad_l, pad_r, pad_t, pad_b = 58, 16, 22, 32
    plot_w, plot_h = width - pad_l - pad_r, height - pad_t - pad_b

    vals = [float(p.get(metric) or 0) for p in points]
    vmax = max(vals + [1.0])
    n = len(vals)
    if n < 2:
        return ""
    step = plot_w / (n - 1)

    def x(i):
        return pad_l + i * step

    def y(v):
        return pad_t + plot_h - (v / vmax) * plot_h

    line = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals))
    area = f"{pad_l},{pad_t + plot_h} " + line + f" {x(n - 1):.1f},{pad_t + plot_h}"

    grid = ""
    for g in range(5):
        gy = pad_t + plot_h - (g / 4) * plot_h
        glabel = _fmt_compact(vmax * g / 4) + meta["unit"]
        grid += (
            f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{width - pad_r}" y2="{gy:.1f}" stroke="#eef1f5" stroke-width="1"/>'
            f'<text x="{pad_l - 8}" y="{gy + 4:.1f}" text-anchor="end" font-size="10" fill="#9aa3b2">{glabel}</text>'
        )

    label_step = max(1, (n - 1) // (8 if layout == "desktop" else 5))
    date_labels = ""
    for i in range(0, n, label_step):
        date_labels += f'<text x="{x(i):.1f}" y="{height - 8}" text-anchor="middle" font-size="10" fill="#9aa3b2">{x_labels[i]}</text>'

    # Точные значения над точками — когда их немного (иначе каша)
    value_labels = ""
    dots = ""
    if n <= 16:
        for i, v in enumerate(vals):
            txt = _fmt(v, meta["decimals"]) if v < 10000 else _fmt_compact(v)
            value_labels += f'<text x="{x(i):.1f}" y="{y(v) - 7:.1f}" text-anchor="middle" font-size="9" font-weight="700" fill="#475569">{txt}</text>'
            dots += f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="2.6" fill="{meta["color"]}" stroke="#fff" stroke-width="1.2"/>'

    return f"""
    <div class="panel">
      <h2><span class="metric-dot" style="background:{meta['color']};"></span>{meta['label']}{title_suffix}</h2>
      <svg width="100%" viewBox="0 0 {width} {height}" role="img">
        {grid}
        <polygon points="{area}" fill="{meta['color']}" fill-opacity="0.09"/>
        <polyline points="{line}" fill="none" stroke="{meta['color']}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
        {dots}
        {value_labels}
        {date_labels}
      </svg>
    </div>"""


def _main_chart_svg(daily: list, layout: str, metrics: list | None = None) -> str:
    """Главный график дашборда по выбранным метрикам (1-2): первая — область с осью Y,
    вторая — пунктирная линия в относительной шкале."""
    if not daily or len(daily) < 2:
        return ""
    metrics = [m for m in (metrics or ["cost", "clicks"]) if m in _CHART_METRIC_META][:2]
    if not metrics:
        metrics = ["cost"]

    width = 900 if layout == "desktop" else 420
    height = 260 if layout == "desktop" else 210
    pad_l, pad_r, pad_t, pad_b = 52, 16, 14, 34
    plot_w, plot_h = width - pad_l - pad_r, height - pad_t - pad_b

    points = []
    for item in daily:
        cost = (
            float(item.get("cost_yandex") or 0) * VAT_RATE
            + float(item.get("cost_vk") or 0) * VAT_RATE
            + float(item.get("cost_avito") or 0)
        )
        points.append({
            "date": str(item.get("date") or ""),
            "cost": cost,
            "clicks": int(item.get("clicks") or 0),
            "impressions": int(item.get("impressions") or 0),
            "leads": int(item.get("leads") or 0),
        })

    n = len(points)
    step = plot_w / (n - 1)

    def x(i):
        return pad_l + i * step

    def series(metric):
        vals = [float(p.get(metric) or 0) for p in points]
        vmax = max(vals + [1.0])
        return vals, vmax

    svg_layers = ""
    legend = ""
    primary = metrics[0]
    p_meta = _CHART_METRIC_META[primary]
    p_vals, p_max = series(primary)

    def y_for(v, vmax):
        return pad_t + plot_h - (v / vmax) * plot_h

    line = " ".join(f"{x(i):.1f},{y_for(v, p_max):.1f}" for i, v in enumerate(p_vals))
    area = f"{pad_l},{pad_t + plot_h} " + line + f" {x(n - 1):.1f},{pad_t + plot_h}"
    svg_layers += (
        f'<polygon points="{area}" fill="{p_meta["color"]}" fill-opacity="0.10"/>'
        f'<polyline points="{line}" fill="none" stroke="{p_meta["color"]}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
    )
    legend += f'<span class="lg"><i style="background:{p_meta["color"]};"></i> {p_meta["label"]}{p_meta["unit"] and " (₽, левая шкала)" or " (левая шкала)"}</span>'

    if len(metrics) > 1:
        secondary = metrics[1]
        s_meta = _CHART_METRIC_META[secondary]
        s_vals, s_max = series(secondary)
        s_line = " ".join(f"{x(i):.1f},{y_for(v, s_max):.1f}" for i, v in enumerate(s_vals))
        svg_layers += (
            f'<polyline points="{s_line}" fill="none" stroke="{s_meta["color"]}" stroke-width="1.6" stroke-dasharray="5 4" stroke-linejoin="round" stroke-linecap="round"/>'
        )
        legend += f'<span class="lg"><i style="background:{s_meta["color"]};"></i> {s_meta["label"]} (относительная шкала)</span>'

    grid = ""
    for f in range(5):
        gy = pad_t + plot_h - (f / 4) * plot_h
        label = _fmt_compact(p_max * f / 4) + p_meta["unit"]
        grid += (
            f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{width - pad_r}" y2="{gy:.1f}" stroke="#eef1f5" stroke-width="1"/>'
            f'<text x="{pad_l - 8}" y="{gy + 4:.1f}" text-anchor="end" font-size="10" fill="#9aa3b2">{label}</text>'
        )

    label_step = max(1, (n - 1) // (8 if layout == "desktop" else 5))
    date_labels = ""
    for i in range(0, n, label_step):
        d = points[i]["date"]
        short = f"{d[8:10]}.{d[5:7]}" if len(d) >= 10 else d
        date_labels += f'<text x="{x(i):.1f}" y="{height - 8}" text-anchor="middle" font-size="10" fill="#9aa3b2">{short}</text>'

    title = " и ".join(_CHART_METRIC_META[m]["label"].lower() for m in metrics).capitalize() + " по дням"
    return f"""
    <div class="panel">
      <h2>{title}</h2>
      <svg width="100%" viewBox="0 0 {width} {height}" role="img">
        {grid}
        {svg_layers}
        {date_labels}
      </svg>
      <div class="chart-legend">{legend}</div>
    </div>"""


def _channels_block(channels: list, layout: str) -> str:
    """Блок «Каналы» — как канальные карточки дашборда: расход / клики / лиды / CPL."""
    if not channels:
        return ""
    rows = ""
    for ch in channels:
        meta = _CHANNEL_META.get(str(ch.get("code")), {"name": ch.get("code"), "color": "#64748b", "soft": "#f5f7f9", "short": "?"})
        expenses = _with_channel_vat(ch.get("expenses"), ch.get("code"))
        clicks = int(ch.get("clicks") or 0)
        leads = int(ch.get("leads") or 0)
        # CPL — от лидового расхода канала (ТЗ VK п.3/№10).
        _lcbp = ch.get("lead_cost_by_platform") or {}
        _lead_raw = _lcbp.get(str(ch.get("code")))
        lead_expenses = _with_channel_vat(_lead_raw if _lead_raw is not None else ch.get("expenses"), ch.get("code"))
        cpl = lead_expenses / leads if leads > 0 else 0
        rows += f"""<tr>
          <td class="ch-name">
            <span class="ch-chip" style="background:{meta['soft']};color:{meta['color']};">{meta['short']}</span>
            {meta['name']}
          </td>
          <td class="num">{_fmt(expenses)} ₽</td>
          <td class="num">{_fmt(clicks)}</td>
          <td class="num">{_fmt(leads)} шт.</td>
          <td class="num">{(_fmt(cpl, 2) + ' ₽') if leads else '—'}</td>
        </tr>"""
    return f"""
    <div class="panel">
      <h2>Каналы</h2>
      <table class="channels-table">
        <thead><tr><th>Канал</th><th class="num">Расход</th><th class="num">Клики</th><th class="num">Лиды</th><th class="num">CPL</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""


def render_report_html(data: dict, layout: str = "desktop") -> str:
    layout = "mobile" if str(layout).lower() == "mobile" else "desktop"
    s = data.get("summary", {})
    tc = data.get("top_campaigns", [])
    client_name = data.get("client_name", "")
    ai_comment = data.get("ai_comment", "")
    start_date = data.get("start_date", "")
    end_date = data.get("end_date", "")
    generated_at = data.get("generated_at", "")
    trends = s.get("trends") if isinstance(s.get("trends"), dict) else None
    sections = data.get("sections") or ["kpi", "chart", "channels", "campaigns"]
    chart_metrics = data.get("chart_metrics") or ["cost", "clicks"]

    summary_platform = _summary_platform(data, tc)

    expenses = _with_cost_breakdown_vat(s.get("expenses", 0), s.get("cost_by_platform"), summary_platform)
    # CPL — от лидового расхода (ТЗ VK п.3/№10), не от всего расхода канала.
    lead_expenses = _with_cost_breakdown_vat(
        s.get("expenses", 0), s.get("lead_cost_by_platform") or s.get("cost_by_platform"), summary_platform
    )
    impressions = int(s.get("impressions", 0))
    clicks = int(s.get("clicks", 0))
    leads = int(s.get("leads", 0))
    cpc = expenses / clicks if clicks > 0 else _with_channel_vat(s.get("cpc", 0), summary_platform)
    cpa = lead_expenses / leads if leads > 0 else _with_channel_vat(s.get("cpa", 0), summary_platform)

    cards = [
        _kpi_card("expenses", "Расходы", f"{_fmt(expenses)} ₽", "За период", trends),
        _kpi_card("impressions", "Показы", _fmt(impressions), "По всем каналам", trends),
        _kpi_card("clicks", "Клики", _fmt(clicks), "Все переходы", trends),
        _kpi_card("cpc", "CPC", f"{_fmt(cpc, 2)} ₽", "Стоимость клика", trends),
        _kpi_card("leads", "Лиды", f"{_fmt(leads)} шт.", "По всем каналам", trends),
        _kpi_card("cpa", "CPL", f"{_fmt(cpa, 2)} ₽", "Стоимость лида", trends),
    ]
    # KPI-сетка на таблице (Grid в WeasyPrint не работает): desktop 3×2, mobile 2×3
    per_row = 3 if layout == "desktop" else 2
    kpi_rows = ""
    for i in range(0, len(cards), per_row):
        cells = "".join(f'<td class="kpi-cell">{c}</td>' for c in cards[i:i + per_row])
        kpi_rows += f"<tr>{cells}</tr>"
    kpi_html = f'<table class="kpi-grid">{kpi_rows}</table>' if "kpi" in sections else ""

    chart_html = ""
    daily_rows = data.get("daily") or []
    if "chart" in sections and len(daily_rows) >= 2:
        day_points = []
        day_labels = []
        for item in daily_rows:
            cost = (
                float(item.get("cost_yandex") or 0) * VAT_RATE
                + float(item.get("cost_vk") or 0) * VAT_RATE
                + float(item.get("cost_avito") or 0)
            )
            day_points.append(_metric_value_from({**item, "cost": cost}))
            d = str(item.get("date") or "")
            day_labels.append(f"{d[8:10]}.{d[5:7]}" if len(d) >= 10 else d)
        for metric in [m for m in chart_metrics if m in _CHART_METRIC_META]:
            chart_html += _single_metric_chart(day_points, metric, layout, day_labels, " по дням")
    channels_html = _channels_block(data.get("channels") or [], layout) if "channels" in sections else ""

    campaigns_rows = ""
    mobile = layout == "mobile"
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
        if mobile:
            campaigns_rows += (
                f'<tr style="background:{bg};">'
                f"<td>{name}</td>"
                f'<td class="num">{cost} ₽</td>'
                f'<td class="num">{conv} шт.</td>'
                f'<td class="num">{c_cpa}{" ₽" if conv else ""}</td>'
                f"</tr>"
            )
        else:
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
    if tc and "campaigns" in sections:
        head = (
            "<tr><th>Кампания</th><th class='num'>Расход</th><th class='num'>Лиды</th><th class='num'>CPL</th></tr>"
            if mobile else
            "<tr><th>Название кампании</th><th class='num'>Расход</th><th class='num'>Показы</th><th class='num'>Клики</th>"
            "<th class='num'>CPC</th><th class='num'>Лиды</th><th class='num'>CPL</th></tr>"
        )
        campaigns_html = f"""
    <div class="panel campaigns-panel">
      <h2>Лучшие рекламные кампании</h2>
      <table class="camp-table">
        <thead>{head}</thead>
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

    # Опциональный блок «Динамика по месяцам» (данные из dynamics_service)
    dynamics_html = ""
    dyn_periods = (data.get("dynamics") or {}).get("periods") or []
    if dyn_periods and len(dyn_periods) >= 2:
        dynamics_metrics = [m for m in (data.get("dynamics_metrics") or ["cost"]) if m in _CHART_METRIC_META]
        dyn_points = []
        dyn_labels = []
        has_incomplete = False
        for p in dyn_periods:
            cost = _with_cost_breakdown_vat(p.get("cost", 0), p.get("cost_by_platform"))
            dyn_points.append(_metric_value_from({**p, "cost": cost}))
            label = str(p.get("label", ""))
            dyn_labels.append(label if len(label) <= 12 else label[:12])
            has_incomplete = has_incomplete or bool(p.get("incomplete"))
        for metric in dynamics_metrics:
            dynamics_html += _single_metric_chart(dyn_points, metric, layout, dyn_labels, " · динамика по месяцам")
        if has_incomplete and dynamics_html:
            dynamics_html += '<div style="font-size:11px;color:#94a3b8;margin:-8px 4px 14px;">* текущий период ещё не завершён</div>' 

    page_size = "1120px 1584px" if layout == "desktop" else "480px 1040px"
    max_width = "1040px" if layout == "desktop" else "440px"
    body_pad = "24px" if layout == "desktop" else "12px"
    kpi_value_size = "20px" if layout == "desktop" else "16px"

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Отчёт за период {start_date} — {end_date}</title>
  <style>
    @page {{ size: {page_size}; margin: 0; }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #f3f4f8;
      color: #09183F;
      line-height: 1.5;
      padding: {body_pad};
    }}
    .dashboard {{ max-width: {max_width}; margin: 0 auto; }}

    .header {{
      background: linear-gradient(135deg, #2563EB 0%, #1d4ed8 50%, #1e40af 100%);
      color: #fff;
      padding: 22px 26px;
      border-radius: 16px;
      margin-bottom: 18px;
    }}
    .header h1 {{ font-size: 19px; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 5px; }}
    .header-period {{ font-size: 14px; font-weight: 600; opacity: 0.95; }}
    .header-project {{ font-size: 12px; opacity: 0.85; margin-top: 4px; }}

    /* KPI: таблица вместо grid (WeasyPrint) */
    .kpi-grid {{ width: 100%; border-collapse: separate; border-spacing: 12px; margin: -12px -12px 8px; }}
    .kpi-cell {{ width: {100 // per_row}%; vertical-align: top; }}
    .kpi-card {{
      background: #fff;
      border-radius: 16px;
      padding: 14px 16px;
    }}
    .kpi-inner {{ border-collapse: collapse; width: 100%; }}
    .kpi-icon-cell {{ width: 46px; vertical-align: top; }}
    .kpi-icon {{
      width: 38px; height: 38px; border-radius: 10px;
      text-align: center; padding-top: 9px;
    }}
    .kpi-label {{ font-size: 10px; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }}
    .kpi-value {{ font-size: {kpi_value_size}; font-weight: 700; color: #09183F; letter-spacing: -0.02em; margin-top: 1px; }}
    .kpi-sub {{ font-size: 10px; color: #94a3b8; margin-top: 3px; }}

    .panel {{
      background: #fff;
      border-radius: 16px;
      padding: 20px 24px;
      margin-bottom: 16px;
    }}
    .panel h2 {{ font-size: 15px; font-weight: 600; color: #09183F; margin-bottom: 14px; }}

    .metric-dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 7px; }}
    .chart-legend {{ margin-top: 8px; color: #64748b; font-size: 11px; }}
    .chart-legend .lg {{ margin-right: 16px; }}
    .chart-legend i {{ display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 5px; }}

    .channels-table {{ width: 100%; border-collapse: separate; border-spacing: 0 8px; }}
    .channels-table th {{ font-size: 11px; color: #b3b3b3; font-weight: 500; padding: 0 12px 2px; text-align: left; }}
    .channels-table td {{ padding: 12px; font-size: 13px; color: #4b4b4b; background: #f8fafc; }}
    .channels-table tr td:first-child {{ border-radius: 10px 0 0 10px; font-weight: 600; color: #09183F; }}
    .channels-table tr td:last-child {{ border-radius: 0 10px 10px 0; }}
    .ch-chip {{
      display: inline-block; width: 24px; height: 24px; border-radius: 7px;
      text-align: center; font-size: 11px; font-weight: 800; padding-top: 3px; margin-right: 8px;
    }}

    .camp-table {{ border-collapse: separate; border-spacing: 0 8px; width: 100%; }}
    .camp-table th {{ font-size: 11px; color: #b3b3b3; font-weight: 500; padding: 0 12px 2px; text-align: left; }}
    .camp-table td {{ padding: 11px 12px; font-size: 12px; color: #4b4b4b; }}
    .camp-table tr td:first-child {{ border-radius: 10px 0 0 10px; font-weight: 500; }}
    .camp-table tr td:last-child {{ border-radius: 0 10px 10px 0; }}
    .num {{ text-align: right; }}
    th.num {{ text-align: right; }}

    .ai-panel .ai-block {{
      background: #eff6ff;
      border: 1px solid #93c5fd;
      padding: 16px 18px;
      border-radius: 12px;
      font-size: 13px;
      line-height: 1.7;
      color: #1e3a5f;
    }}

    .report-footer {{ text-align: center; padding: 14px; font-size: 11px; color: #94a3b8; font-weight: 500; }}
    .report-footer .brand {{ margin-top: 3px; font-size: 10px; color: #cbd5e1; }}
  </style>
</head>
<body>
  <div class="dashboard">
    <div class="header">
      <h1>Отчёт по рекламным кампаниям</h1>
      <div class="header-period">{start_date} — {end_date}</div>
      {project_line}
    </div>

    {kpi_html}

    {chart_html}
    {channels_html}
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
