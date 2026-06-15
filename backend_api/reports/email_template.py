"""
HTML-шаблон email-отчёта для отправки через UniSender.
Inline-стили для максимальной совместимости с почтовыми клиентами.
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


def _fmt_number(value, decimals=0) -> str:
    if decimals == 0:
        return f"{int(value):,}".replace(",", " ")
    return f"{value:,.{decimals}f}".replace(",", " ")


def _escape(text: str) -> str:
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _kpi_cell(label: str, value: str, color: str = "#09183F") -> str:
    return f"""
    <td style="padding:8px 12px;">
      <table cellpadding="0" cellspacing="0" border="0" width="100%"
             style="background:linear-gradient(145deg,#f8fafc,#f1f5f9);border:1px solid #e2e8f0;border-radius:10px;">
        <tr>
          <td style="padding:14px 16px;">
            <div style="font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:0.04em;margin-bottom:4px;">{label}</div>
            <div style="font-size:20px;font-weight:700;color:{color};letter-spacing:-0.02em;">{value}</div>
          </td>
        </tr>
      </table>
    </td>"""


def render_report_email_html(data: dict) -> str:
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

    project_line = f'<div style="font-size:13px;opacity:0.85;margin-top:4px;">{_escape(client_name)}</div>' if client_name else ""

    kpi_row1 = _kpi_cell("Расходы", f"{_fmt_number(expenses)} ₽")
    kpi_row1 += _kpi_cell("Показы", _fmt_number(impressions))
    kpi_row1 += _kpi_cell("Клики", _fmt_number(clicks))

    kpi_row2 = _kpi_cell("Лиды", f"{_fmt_number(leads)} шт.")
    kpi_row2 += _kpi_cell("CPC", f"{_fmt_number(cpc, 2)} ₽")
    kpi_row2 += _kpi_cell("CPL", f"{_fmt_number(cpa, 2)} ₽")

    _tint_colors = ["#fff4ee", "#eafcf0", "#e8eefc"]
    campaigns_html = ""
    if tc:
        rows = ""
        for i, c in enumerate(tc[:10]):
            name = _escape(c.get("name", c.get("campaign_name", "—")))
            c_platform = _campaign_platform(c)
            conv = int(c.get("conversions", 0))
            cost = f"{_fmt_number(_with_channel_vat(c.get('cost', 0), c_platform))} ₽"
            cpa_val = f"{_fmt_number(_with_channel_vat(c.get('cpa', 0), c_platform), 2)} ₽" if conv else "—"
            bg = _tint_colors[i % len(_tint_colors)]
            td_style = "padding:12px 14px;font-size:13px;color:#4b4b4b;"
            rows += f"""
            <tr style="background:{bg};">
              <td style="{td_style}">{name}</td>
              <td style="{td_style}text-align:center;">{conv} шт.</td>
              <td style="{td_style}text-align:right;">{cost}</td>
              <td style="{td_style}text-align:right;">{cpa_val}</td>
            </tr>"""

        campaigns_html = f"""
        <tr><td style="padding:28px 32px 0;">
          <div style="font-size:16px;font-weight:600;color:#09183F;margin-bottom:16px;">
            Лучшие рекламные кампании
          </div>
          <table cellpadding="0" cellspacing="8" border="0" width="100%">
            <thead>
              <tr>
                <th style="padding:0 14px 4px;font-size:12px;font-weight:500;color:#b3b3b3;text-align:left;">Кампания</th>
                <th style="padding:0 14px 4px;font-size:12px;font-weight:500;color:#b3b3b3;text-align:center;">Лиды</th>
                <th style="padding:0 14px 4px;font-size:12px;font-weight:500;color:#b3b3b3;text-align:right;">Расход</th>
                <th style="padding:0 14px 4px;font-size:12px;font-weight:500;color:#b3b3b3;text-align:right;">CPL</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </td></tr>"""

    comment_html = ""
    if ai_comment:
        escaped = _escape(ai_comment).replace("\n", "<br>")
        comment_html = f"""
        <tr><td style="padding:24px 32px 0;">
          <div style="font-size:12px;font-weight:600;color:#2563EB;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px;">
            Комментарий ИИ
          </div>
          <div style="background:linear-gradient(145deg,#eff6ff,#dbeafe);border:1px solid #93c5fd;padding:18px 20px;border-radius:10px;font-size:13px;line-height:1.65;color:#1e3a5f;">
            {escaped}
          </div>
        </td></tr>"""

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>Отчёт {start_date} — {end_date}</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;-webkit-font-smoothing:antialiased;">

  <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#f1f5f9;">
    <tr><td align="center" style="padding:24px 16px;">

      <table cellpadding="0" cellspacing="0" border="0" width="600" style="max-width:600px;width:100%;">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#2563EB 0%,#1d4ed8 50%,#1e40af 100%);padding:24px 28px;border-radius:16px 16px 0 0;">
            <div style="font-size:20px;font-weight:700;color:#ffffff;letter-spacing:-0.02em;margin-bottom:6px;">
              Отчёт по рекламным кампаниям
            </div>
            <div style="font-size:15px;font-weight:600;color:#ffffff;opacity:0.95;">
              {start_date} — {end_date}
            </div>
            {project_line}
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="background:#ffffff;padding:0;border-radius:0 0 16px 16px;">
            <table cellpadding="0" cellspacing="0" border="0" width="100%">

              <!-- KPI -->
              <tr><td style="padding:24px 32px 0;">
                <div style="font-size:12px;font-weight:600;color:#2563EB;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px;">
                  Ключевые показатели
                </div>
              </td></tr>

              <tr><td style="padding:0 20px;">
                <table cellpadding="0" cellspacing="0" border="0" width="100%">
                  <tr>{kpi_row1}</tr>
                  <tr>{kpi_row2}</tr>
                </table>
              </td></tr>

              {comment_html}
              {campaigns_html}

              <!-- Footer inside card -->
              <tr><td style="padding:24px 32px;text-align:center;">
                <div style="font-size:11px;color:#94a3b8;font-weight:500;">
                  Сформировано {generated_at}
                </div>
              </td></tr>

            </table>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:16px 28px;text-align:center;">
            <div style="font-size:11px;color:#94a3b8;">
              AdMirra — аналитика рекламных кампаний
            </div>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>

</body>
</html>"""
