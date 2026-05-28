"""
Конвертация PNG-скриншота дашборда в PDF с помощью WeasyPrint.
Опционально добавляет AI-комментарий под скриншотом.
"""
from typing import Optional


def png_to_pdf(png_bytes: bytes, ai_comment: Optional[str] = None) -> bytes:
    import base64
    from weasyprint import HTML

    b64 = base64.b64encode(png_bytes).decode()

    comment_html = ""
    if ai_comment and ai_comment.strip():
        escaped = (
            ai_comment.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("\n", "<br>")
        )
        comment_html = f"""
        <div style="margin:20px auto 0;max-width:960px;background:#fff;border-radius:16px;
                    padding:24px 28px;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
          <h2 style="font-size:16px;font-weight:600;color:#09183F;margin:0 0 16px;">
            Комментарий ИИ к отчёту
          </h2>
          <div style="background:linear-gradient(145deg,#eff6ff,#dbeafe);border:1px solid #93c5fd;
                      padding:20px 22px;border-radius:12px;font-size:14px;line-height:1.7;
                      white-space:pre-wrap;color:#1e3a5f;">
            {escaped}
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      background: #f3f4f8;
      padding: 0;
    }}
    @page {{
      size: A4 landscape;
      margin: 12mm;
    }}
    .screenshot {{
      width: 100%;
      display: block;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }}
    .footer {{
      text-align: center;
      padding: 16px;
      font-size: 11px;
      color: #94a3b8;
    }}
  </style>
</head>
<body>
  <img class="screenshot" src="data:image/png;base64,{b64}" />
  {comment_html}
  <div class="footer">AdMirra — аналитика рекламных кампаний</div>
</body>
</html>"""

    return HTML(string=html).write_pdf()
