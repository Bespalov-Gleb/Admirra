"""
Роутер отчётов: PDF, PNG, DOCX, отправка в Email и Telegram.
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
import uuid

from core.database import get_db
from core import models, security
from backend_api.services.subscription import SubscriptionService
from backend_api.services.history import log_history_event
from backend_api.reports.pdf_service import generate_report_pdf
from backend_api.reports.export_service import (
    generate_report_png,
    generate_report_docx,
    save_report_for_link,
    get_report_file_by_token,
    save_report_view_data,
    get_report_view_data,
    _get_report_data,
)
from backend_api.reports.report_html import render_report_html

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])


def _log_report_export(
    db: Session,
    current_user: models.User,
    fmt: str,
    client_id: Optional[uuid.UUID],
    start_date: str,
    end_date: str,
) -> None:
    log_history_event(
        db,
        actor=current_user,
        event_type="report",
        action="report_exported",
        description=f"Экспорт отчета в формате {fmt}",
        client_id=client_id,
        target_type="report_export",
        meta={"format": fmt, "start_date": start_date, "end_date": end_date},
    )


class SendReportRequest(BaseModel):
    report_type: str = "ai"  # pdf | ai | text
    channels: List[str]  # ["email", "telegram", "max"]
    email_recipients: Optional[List[str]] = None
    telegram_chat_id: Optional[str] = None
    max_chat_id: Optional[str] = None
    max_user_id: Optional[str] = None
    client_id: Optional[str] = None
    start_date: str
    end_date: str
    comment: Optional[str] = None  # готовый текст — если передан, не генерируем заново
    screenshot_base64: Optional[str] = None  # PNG скриншот дашборда (base64)


@router.get("/pdf")
async def get_report_pdf(
    start_date: str = Query(...),
    end_date: str = Query(...),
    client_id: Optional[str] = Query(None),
    ai: bool = Query(False, description="Генерировать отчёт с ИИ"),
    comment: Optional[str] = Query(None, description="Готовый комментарий (если есть — не генерируем)"),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Скачивание PDF-отчёта за указанный период. При ai=true — с AI-комментарием.
    Если передан comment — используется он вместо генерации.
    """
    u_client_id = None
    if client_id:
        try:
            u_client_id = uuid.UUID(client_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный client_id")

    use_comment = (comment or "").strip() if comment else None
    if ai and not use_comment:
        try:
            logger.info("PDF report: generating AI comment (ai=true)")
            from ai.report_generator import generate_report
            use_comment = await generate_report(
                db=db,
                user_id=current_user.id,
                client_id=u_client_id,
                start_date=start_date,
                end_date=end_date,
                report_type="full",
            )
            if not use_comment or not str(use_comment).strip():
                logger.warning("PDF report: AI returned empty comment, using fallback")
                use_comment = "AI не удалось сформировать комментарий. Проверьте настройки OPENAI_API_KEY в .env и доступность API."
            else:
                logger.info("PDF report: AI comment received, length=%d", len(str(use_comment)))
        except Exception as e:
            logger.exception("AI report generation failed: %s", e)
            raise HTTPException(status_code=500, detail="Не удалось сформировать AI-отчёт")

    try:
        pdf_bytes = generate_report_pdf(
            db=db,
            user_id=current_user.id,
            client_id=u_client_id,
            start_date=start_date,
            end_date=end_date,
            comment=use_comment,
        )
        filename = f"report_{start_date}_{end_date}.pdf"
        _log_report_export(db, current_user, "pdf", u_client_id, start_date, end_date)
        db.commit()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("PDF generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Не удалось сформировать PDF")


@router.get("/png")
async def get_report_png(
    start_date: str = Query(...),
    end_date: str = Query(...),
    client_id: Optional[str] = Query(None),
    ai: bool = Query(False),
    comment: Optional[str] = Query(None),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Скачивание PNG-отчёта (первая страница)."""
    u_client_id = None
    if client_id:
        try:
            u_client_id = uuid.UUID(client_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный client_id")
    use_comment = (comment or "").strip() if comment else None
    if ai and not use_comment:
        try:
            from ai.report_generator import generate_report
            use_comment = await generate_report(
                db=db, user_id=current_user.id, client_id=u_client_id,
                start_date=start_date, end_date=end_date, report_type="full",
            )
            if not use_comment or not str(use_comment).strip():
                use_comment = "AI не удалось сформировать комментарий."
        except Exception as e:
            logger.exception("AI report failed: %s", e)
            raise HTTPException(status_code=500, detail="Не удалось сформировать AI-отчёт")
    try:
        png_bytes = generate_report_png(
            db=db, user_id=current_user.id, client_id=u_client_id,
            start_date=start_date, end_date=end_date, comment=use_comment,
        )
        filename = f"report_{start_date}_{end_date}.png"
        _log_report_export(db, current_user, "png", u_client_id, start_date, end_date)
        db.commit()
        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ImportError as e:
        raise HTTPException(status_code=503, detail="PNG-экспорт недоступен. Установите pymupdf.")
    except Exception as e:
        logger.exception("PNG generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Не удалось сформировать PNG")


@router.get("/docx")
async def get_report_docx(
    start_date: str = Query(...),
    end_date: str = Query(...),
    client_id: Optional[str] = Query(None),
    ai: bool = Query(False),
    comment: Optional[str] = Query(None),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Скачивание DOCX-отчёта."""
    u_client_id = None
    if client_id:
        try:
            u_client_id = uuid.UUID(client_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный client_id")
    use_comment = (comment or "").strip() if comment else None
    if ai and not use_comment:
        try:
            from ai.report_generator import generate_report
            use_comment = await generate_report(
                db=db, user_id=current_user.id, client_id=u_client_id,
                start_date=start_date, end_date=end_date, report_type="full",
            )
            if not use_comment or not str(use_comment).strip():
                use_comment = "AI не удалось сформировать комментарий."
        except Exception as e:
            logger.exception("AI report failed: %s", e)
            raise HTTPException(status_code=500, detail="Не удалось сформировать AI-отчёт")
    try:
        docx_bytes = generate_report_docx(
            db=db, user_id=current_user.id, client_id=u_client_id,
            start_date=start_date, end_date=end_date, comment=use_comment,
        )
        filename = f"report_{start_date}_{end_date}.docx"
        _log_report_export(db, current_user, "docx", u_client_id, start_date, end_date)
        db.commit()
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ImportError as e:
        raise HTTPException(status_code=503, detail="DOCX-экспорт недоступен. Установите python-docx.")
    except Exception as e:
        logger.exception("DOCX generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Не удалось сформировать DOCX")


class DownloadReportRequest(BaseModel):
    """Тело запроса для скачивания отчёта (POST) — comment в body избегает лимита длины URL."""
    start_date: str
    end_date: str
    client_id: Optional[str] = None
    ai: bool = False
    comment: Optional[str] = None


async def _resolve_report_comment(
    *,
    ai: bool,
    comment: Optional[str],
    db: Session,
    user_id: uuid.UUID,
    client_id: Optional[uuid.UUID],
    start_date: str,
    end_date: str,
) -> Optional[str]:
    """Возвращает комментарий: готовый или сгенерированный AI."""
    use_comment = (comment or "").strip() if comment else None
    if ai and not use_comment:
        try:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if user:
                SubscriptionService.ensure_can_use_ai(db, user, requested=1)
            from ai.report_generator import generate_report
            use_comment = await generate_report(
                db=db, user_id=user_id, client_id=client_id,
                start_date=start_date, end_date=end_date, report_type="full",
            )
            if not use_comment or not str(use_comment).strip():
                use_comment = "AI не удалось сформировать комментарий."
            if user:
                SubscriptionService.increment_ai_usage(db, user, requested=1)
                db.commit()
        except Exception as e:
            logger.exception("AI report failed: %s", e)
            raise HTTPException(status_code=500, detail="Не удалось сформировать AI-отчёт")
    return use_comment


@router.post("/docx")
async def post_report_docx(
    req: DownloadReportRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Скачивание DOCX-отчёта (POST). Используйте при передаче длинного comment — избегает лимита длины URL."""
    u_client_id = None
    if req.client_id:
        try:
            u_client_id = uuid.UUID(req.client_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный client_id")
    use_comment = await _resolve_report_comment(
        ai=req.ai, comment=req.comment, db=db, user_id=current_user.id,
        client_id=u_client_id, start_date=req.start_date, end_date=req.end_date,
    )
    try:
        docx_bytes = generate_report_docx(
            db=db, user_id=current_user.id, client_id=u_client_id,
            start_date=req.start_date, end_date=req.end_date, comment=use_comment,
        )
        filename = f"report_{req.start_date}_{req.end_date}.docx"
        _log_report_export(db, current_user, "docx", u_client_id, req.start_date, req.end_date)
        db.commit()
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ImportError as e:
        raise HTTPException(status_code=503, detail="DOCX-экспорт недоступен. Установите python-docx.")
    except Exception as e:
        logger.exception("DOCX generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Не удалось сформировать DOCX")


@router.post("/pdf")
async def post_report_pdf(
    req: DownloadReportRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Скачивание PDF-отчёта (POST). Используйте при передаче длинного comment."""
    u_client_id = None
    if req.client_id:
        try:
            u_client_id = uuid.UUID(req.client_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный client_id")
    use_comment = await _resolve_report_comment(
        ai=req.ai, comment=req.comment, db=db, user_id=current_user.id,
        client_id=u_client_id, start_date=req.start_date, end_date=req.end_date,
    )
    try:
        pdf_bytes = generate_report_pdf(
            db=db, user_id=current_user.id, client_id=u_client_id,
            start_date=req.start_date, end_date=req.end_date, comment=use_comment,
        )
        filename = f"report_{req.start_date}_{req.end_date}.pdf"
        _log_report_export(db, current_user, "pdf", u_client_id, req.start_date, req.end_date)
        db.commit()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        logger.exception("PDF generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Не удалось сформировать PDF")


@router.post("/png")
async def post_report_png(
    req: DownloadReportRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Скачивание PNG-отчёта (POST). Используйте при передаче длинного comment."""
    u_client_id = None
    if req.client_id:
        try:
            u_client_id = uuid.UUID(req.client_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный client_id")
    use_comment = await _resolve_report_comment(
        ai=req.ai, comment=req.comment, db=db, user_id=current_user.id,
        client_id=u_client_id, start_date=req.start_date, end_date=req.end_date,
    )
    try:
        png_bytes = generate_report_png(
            db=db, user_id=current_user.id, client_id=u_client_id,
            start_date=req.start_date, end_date=req.end_date, comment=use_comment,
        )
        filename = f"report_{req.start_date}_{req.end_date}.png"
        _log_report_export(db, current_user, "png", u_client_id, req.start_date, req.end_date)
        db.commit()
        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ImportError as e:
        raise HTTPException(status_code=503, detail="PNG-экспорт недоступен. Установите pymupdf.")
    except Exception as e:
        logger.exception("PNG generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Не удалось сформировать PNG")


class CreateLinkRequest(BaseModel):
    start_date: str
    end_date: str
    client_id: Optional[str] = None
    comment: Optional[str] = None  # Готовый комментарий из localStorage — не перегенерируем


@router.post("/link")
async def create_report_link(
    req: CreateLinkRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Создаёт ссылку на страницу с отчётом. Ссылка действительна 24 часа."""
    u_client_id = None
    if req.client_id:
        try:
            u_client_id = uuid.UUID(req.client_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный client_id")
    use_comment = (req.comment or "").strip() if req.comment else None
    if not use_comment:
        try:
            SubscriptionService.ensure_can_use_ai(db, current_user, requested=1)
            from ai.report_generator import generate_report
            use_comment = await generate_report(
                db=db, user_id=current_user.id, client_id=u_client_id,
                start_date=req.start_date, end_date=req.end_date, report_type="full",
            )
            if not use_comment or not str(use_comment).strip():
                use_comment = "AI не удалось сформировать комментарий."
            SubscriptionService.increment_ai_usage(db, current_user, requested=1)
            db.commit()
        except Exception as e:
            logger.exception("AI report failed: %s", e)
            raise HTTPException(status_code=500, detail="Не удалось сформировать AI-отчёт")
    try:
        summary, top_campaigns, client_name, _, sd, ed = _get_report_data(
            db, current_user.id, u_client_id,
            req.start_date, req.end_date, use_comment
        )
        token = save_report_view_data(
            summary=summary,
            top_campaigns=top_campaigns,
            client_name=client_name,
            ai_comment=use_comment or "",
            start_date=req.start_date,
            end_date=req.end_date,
            ttl_seconds=86400,
        )
        return {"url": f"/api/reports/view/{token}", "token": token}
    except Exception as e:
        logger.exception("Link creation failed: %s", e)
        raise HTTPException(status_code=500, detail="Не удалось создать ссылку")


@router.get("/view/{token}")
async def get_report_view(token: str):
    """Страница с отчётом (открывается по ссылке, без авторизации)."""
    data = get_report_view_data(token)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail="Ссылка недействительна или истекла (действует 24 часа)",
        )
    html = render_report_html(data)
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/file/{token}")
async def get_report_file(token: str):
    """Скачивание отчёта по временной ссылке (без авторизации — токен является секретом)."""
    data, media_type, filename = get_report_file_by_token(token)
    if data is None:
        raise HTTPException(status_code=404, detail="Ссылка недействительна или истекла")
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/send")
async def send_report(
    req: SendReportRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Отправка отчёта по каналам: Email, Telegram.
    """
    u_client_id = None
    if req.client_id:
        try:
            u_client_id = uuid.UUID(req.client_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный client_id")

    pdf_bytes = None
    png_bytes = None
    ai_text = None

    # Скриншот дашборда с фронтенда (base64 PNG)
    if req.screenshot_base64:
        import base64
        try:
            png_bytes = base64.b64decode(req.screenshot_base64)
            logger.info("send_report: received dashboard screenshot (%d bytes)", len(png_bytes))
        except Exception as e:
            logger.warning("send_report: invalid screenshot_base64: %s", e)

    # Если передан готовый текст — используем его напрямую, не генерируем заново
    if req.comment and req.comment.strip():
        ai_text = req.comment.strip()
        logger.info("send_report: using provided comment text (len=%d), skipping AI generation", len(ai_text))
    elif req.report_type in ("ai", "text"):
        try:
            SubscriptionService.ensure_can_use_ai(db, current_user, requested=1)
            from ai.report_generator import generate_report
            ai_text = await generate_report(
                db=db,
                user_id=current_user.id,
                client_id=u_client_id,
                start_date=req.start_date,
                end_date=req.end_date,
                report_type="full",
            )
            SubscriptionService.increment_ai_usage(db, current_user, requested=1)
            db.commit()
        except Exception as e:
            logger.warning("AI report generation skipped: %s", e)

    # Конвертируем скриншот в PDF, или генерируем PDF из HTML-шаблона
    if png_bytes:
        try:
            from backend_api.reports.screenshot_to_pdf import png_to_pdf
            pdf_bytes = png_to_pdf(png_bytes, ai_text)
        except Exception as e:
            logger.exception("Screenshot to PDF failed: %s", e)
    if not pdf_bytes:
        try:
            pdf_bytes = generate_report_pdf(
                db=db,
                user_id=current_user.id,
                client_id=u_client_id,
                start_date=req.start_date,
                end_date=req.end_date,
                comment=ai_text,
            )
        except Exception as e:
            logger.exception("PDF generation failed: %s", e)

    results = {"email": False, "telegram": False, "max": False, "email_error": None}

    # Email (UniSender Go → SMTP fallback)
    if "email" in req.channels and req.email_recipients:
        try:
            subject = f"Отчёт за период {req.start_date} — {req.end_date}"
            from backend_api.services.unisender import is_configured as unisender_ok, send_report_email as uni_send
            if unisender_ok():
                from backend_api.reports.email_template import render_report_email_html
                from datetime import datetime as _dt
                report_data = _get_report_data(
                    db, current_user.id, u_client_id,
                    req.start_date, req.end_date, None,
                )
                summary, top_campaigns, client_name, _, _, _ = report_data
                email_data = {
                    "summary": summary,
                    "top_campaigns": top_campaigns,
                    "client_name": client_name or "",
                    "ai_comment": ai_text or "",
                    "start_date": req.start_date,
                    "end_date": req.end_date,
                    "generated_at": _dt.now().strftime("%Y-%m-%d %H:%M"),
                }
                html_body = render_report_email_html(email_data)
                plain_body = ai_text or f"Отчёт по рекламным кампаниям за период {req.start_date} — {req.end_date}."
                ok, err = await uni_send(
                    recipients=req.email_recipients,
                    subject=subject,
                    html_body=html_body,
                    plain_body=plain_body,
                    pdf_bytes=pdf_bytes,
                    filename=f"report_{req.start_date}_{req.end_date}.pdf",
                )
            else:
                from lead_validator.services.email_sender import email_sender
                body_text = ai_text or f"Отчёт по рекламным кампаниям за период {req.start_date} — {req.end_date}."
                ok, err = await email_sender.send_report_email(
                    recipients=req.email_recipients,
                    subject=subject,
                    body=body_text,
                    pdf_bytes=pdf_bytes if pdf_bytes else None,
                    filename=f"report_{req.start_date}_{req.end_date}.pdf",
                )
            results["email"] = ok
            if err:
                results["email_error"] = err
        except Exception as e:
            logger.exception("Email send failed: %s", e)
            results["email_error"] = str(e)

    # Telegram — всегда отправляем PDF как документ (скриншот дашборда)
    if "telegram" in req.channels and req.telegram_chat_id:
        try:
            from lead_validator.services.telegram import telegram_notifier
            if pdf_bytes:
                caption = f"📊 Отчёт за период {req.start_date} — {req.end_date}"
                results["telegram"] = await telegram_notifier.send_document(
                    chat_id=req.telegram_chat_id,
                    document=pdf_bytes,
                    filename=f"report_{req.start_date}_{req.end_date}.pdf",
                    caption=caption,
                )
            elif ai_text:
                header = f"📊 AI-отчёт за период {req.start_date} — {req.end_date}\n\n"
                results["telegram"] = await telegram_notifier.send_message(
                    text=header + ai_text,
                    parse_mode=None,
                    chat_id=req.telegram_chat_id,
                )
            else:
                raise HTTPException(status_code=400, detail="Нет данных для отправки в Telegram")
        except ImportError:
            raise HTTPException(status_code=503, detail="Модуль Telegram недоступен")
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Telegram send failed: %s", e)

    # MAX reports bot
    if "max" in req.channels:
        max_chat_id = (req.max_chat_id or current_user.report_max_chat_id or "").strip()
        max_user_id = (req.max_user_id or current_user.report_max_user_id or "").strip()
        if not max_chat_id and not max_user_id:
            raise HTTPException(status_code=400, detail="MAX для отчётов не привязан")
        try:
            from backend_api.services import max_reports_bot

            body_text = ai_text or f"Отчёт за период {req.start_date} — {req.end_date} сформирован."
            header = f"AI-отчёт за период {req.start_date} — {req.end_date}\n\n" if ai_text else ""
            results["max"] = await max_reports_bot.send_message(
                header + body_text,
                chat_id=max_chat_id or None,
                user_id=max_user_id or None,
            )
        except Exception as e:
            logger.exception("MAX report send failed: %s", e)

    if "email" in req.channels and req.email_recipients:
        log_history_event(
            db,
            actor=current_user,
            event_type="report",
            action="report_sent_email",
            description="Отправка отчета по Email",
            client_id=u_client_id,
            target_type="report_delivery",
            meta={"ok": bool(results.get("email")), "recipients": req.email_recipients},
        )
    if "telegram" in req.channels and req.telegram_chat_id:
        log_history_event(
            db,
            actor=current_user,
            event_type="report",
            action="report_sent_telegram",
            description="Отправка отчета в Telegram",
            client_id=u_client_id,
            target_type="report_delivery",
            meta={"ok": bool(results.get("telegram")), "chat_id": req.telegram_chat_id},
        )
    if "max" in req.channels:
        log_history_event(
            db,
            actor=current_user,
            event_type="report",
            action="report_sent_max",
            description="Отправка отчета в MAX",
            client_id=u_client_id,
            target_type="report_delivery",
            meta={"ok": bool(results.get("max"))},
        )
    db.commit()
    return {"ok": True, "results": results}
