"""
Роутер отчётов: PDF, PNG, DOCX, отправка в Email и Telegram.
"""
import logging
from typing import Optional, List
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session, defer
import uuid

from core.database import get_db
from core import models, schemas, security
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


def _wants_dynamics(user) -> bool:
    """Opt-in блока «Динамика» из JSON расписания пользователя."""
    try:
        import json
        sched = json.loads(user.report_schedule) if getattr(user, "report_schedule", None) else {}
        return bool(sched.get("include_dynamics"))
    except Exception:
        return False

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
    folder_id: Optional[str] = None  # скоуп «папка»: сводный отчёт по вложенным проектам
    folder_per_branch: bool = False  # «комплект по каждому филиалу» + сводный
    start_date: str
    end_date: str
    comment: Optional[str] = None  # готовый текст — если передан, не генерируем заново
    screenshot_base64: Optional[str] = None  # PNG скриншот дашборда (base64)


@router.get("/pdf")
async def get_report_pdf(
    start_date: str = Query(...),
    end_date: str = Query(...),
    client_id: Optional[str] = Query(None),
    folder_id: Optional[str] = Query(None),
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
                folder_id=folder_id,
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
            include_dynamics=_wants_dynamics(current_user),
            folder_id=folder_id,
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
    folder_id: Optional[str] = Query(None),
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
                folder_id=folder_id,
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
            folder_id=folder_id,
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
    folder_id: Optional[str] = Query(None),
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
                folder_id=folder_id,
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
            folder_id=folder_id,
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
    folder_id: Optional[str] = None  # скоуп «папка»
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
    folder_id: Optional[str] = None,
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
                folder_id=folder_id,
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
        folder_id=req.folder_id,
    )
    try:
        docx_bytes = generate_report_docx(
            db=db, user_id=current_user.id, client_id=u_client_id,
            start_date=req.start_date, end_date=req.end_date, comment=use_comment,
            folder_id=req.folder_id,
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
        folder_id=req.folder_id,
    )
    try:
        pdf_bytes = generate_report_pdf(
            db=db, user_id=current_user.id, client_id=u_client_id,
            start_date=req.start_date, end_date=req.end_date, comment=use_comment,
            include_dynamics=_wants_dynamics(current_user),
            folder_id=req.folder_id,
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
        folder_id=req.folder_id,
    )
    try:
        png_bytes = generate_report_png(
            db=db, user_id=current_user.id, client_id=u_client_id,
            start_date=req.start_date, end_date=req.end_date, comment=use_comment,
            folder_id=req.folder_id,
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
    # ТЗ «Отчёты» (экран 1): экспорт — отдельная ЛЁГКАЯ ветка, без превью и
    # утверждений. В ссылку попадает только готовый комментарий, переданный с
    # дашборда. Синхронная LLM-генерация здесь делала «Получить ссылку»
    # операцией на 15–30 секунд и незаметно списывала AI-кредит; без
    # комментария страница просто не показывает этот блок.
    use_comment = (req.comment or "").strip() if req.comment else None
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
                folder_id=req.folder_id,
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
                include_dynamics=_wants_dynamics(current_user),
                folder_id=req.folder_id,
            )
        except Exception as e:
            logger.exception("PDF generation failed: %s", e)

    # «Комплект по каждому филиалу»: к сводному отчёту папки добавляем PDF по каждому
    # вложенному проекту (email — вложениями в одно письмо, telegram — документами).
    branch_attachments = []
    if req.folder_id and req.folder_per_branch:
        try:
            from backend_api.stats_service import StatsService as _SS
            branch_ids = _SS.resolve_folder_client_ids(db, current_user.id, req.folder_id)
            for _bid in branch_ids:
                _client = db.query(models.Client).filter(models.Client.id == _bid).first()
                if not _client:
                    continue
                try:
                    _pdf = generate_report_pdf(
                        db=db,
                        user_id=current_user.id,
                        client_id=_bid,
                        start_date=req.start_date,
                        end_date=req.end_date,
                        comment=None,
                        include_dynamics=False,
                    )
                    _safe = "".join(ch if ch.isalnum() else "_" for ch in (_client.name or "branch"))[:40]
                    branch_attachments.append((f"report_{_safe}_{req.start_date}_{req.end_date}.pdf", _pdf))
                except Exception as _branch_err:
                    logger.warning("Branch report failed for %s: %s", _bid, _branch_err)
        except Exception as _kit_err:
            logger.warning("Folder per-branch kit failed: %s", _kit_err)

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
                    folder_id=req.folder_id,
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
                    extra_attachments=branch_attachments or None,
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
                for _att_name, _att_bytes in branch_attachments:
                    try:
                        await telegram_notifier.send_document(
                            chat_id=req.telegram_chat_id,
                            document=_att_bytes,
                            filename=_att_name,
                            caption=None,
                        )
                    except Exception as _tg_err:
                        logger.warning("Telegram branch report failed: %s", _tg_err)
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


# ══════════ Правила автоотправки отчётов ══════════

VALID_SCHEDULE_DAYS = {"daily", "weekdays", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
VALID_SCHEDULE_CHANNELS = {"telegram", "max", "email"}
VALID_SCHEDULE_PLATFORMS = {"all", "yandex", "vk", "avito"}
VALID_REPORT_SECTIONS = {"kpi", "chart", "channels", "campaigns"}
VALID_CHART_METRICS = {"cost", "impressions", "clicks", "cpc", "cpa", "leads"}
MAX_SCHEDULES_PER_USER = 20


def _validate_schedule_payload(*, day=None, send_time=None, channels=None, platform=None, period_days=None, report_format=None, sections=None, chart_metrics=None):
    if day is not None and day not in VALID_SCHEDULE_DAYS:
        raise HTTPException(status_code=422, detail="Некорректный день отправки")
    if send_time is not None:
        import re as _re
        if not _re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(send_time)):
            raise HTTPException(status_code=422, detail="Время отправки — в формате ЧЧ:ММ")
    if channels is not None:
        bad = [c for c in channels if c not in VALID_SCHEDULE_CHANNELS]
        if bad:
            raise HTTPException(status_code=422, detail=f"Неизвестный канал доставки: {bad[0]}")
    if platform is not None and platform not in VALID_SCHEDULE_PLATFORMS:
        raise HTTPException(status_code=422, detail="Некорректный рекламный канал")
    if period_days is not None and int(period_days) not in (1, 7, 14, 30):
        raise HTTPException(status_code=422, detail="Период отчёта: 1, 7, 14 или 30 дней")
    if report_format is not None and report_format not in ("desktop", "mobile"):
        raise HTTPException(status_code=422, detail="Формат отчёта: desktop или mobile")
    if sections is not None:
        bad = [s for s in sections if s not in VALID_REPORT_SECTIONS]
        if bad:
            raise HTTPException(status_code=422, detail=f"Неизвестная секция отчёта: {bad[0]}")
        if not sections:
            raise HTTPException(status_code=422, detail="Выберите хотя бы одну секцию отчёта")
    if chart_metrics is not None:
        bad = [m for m in chart_metrics if m not in VALID_CHART_METRICS]
        if bad:
            raise HTTPException(status_code=422, detail=f"Неизвестная метрика графика: {bad[0]}")


def _schedule_scope_label(db: Session, s: models.ReportSchedule) -> str:
    parts = []
    if s.scope_folder_id:
        folder = db.query(models.Folder).filter(models.Folder.id == s.scope_folder_id).first()
        parts.append(f"Папка «{folder.name}»" if folder else "Папка")
    elif s.scope_client_id:
        client = db.query(models.Client).filter(models.Client.id == s.scope_client_id).first()
        parts.append(f"Проект «{client.name}»" if client else "Проект")
    else:
        parts.append("Все проекты")
    platform_names = {"all": "все каналы", "yandex": "Яндекс Директ", "vk": "VK Реклама", "avito": "Avito"}
    parts.append(platform_names.get(s.platform or "all", s.platform))
    return " · ".join(parts)


def _schedule_to_response(db: Session, s: models.ReportSchedule) -> schemas.ReportScheduleResponse:
    import json as _json
    try:
        channels = _json.loads(s.channels) if isinstance(s.channels, str) else (s.channels or [])
    except Exception:
        channels = []
    def _jlist(raw, default):
        try:
            val = _json.loads(raw) if isinstance(raw, str) and raw else raw
            return val if isinstance(val, list) and val else default
        except Exception:
            return default
    return schemas.ReportScheduleResponse(
        id=s.id,
        name=s.name,
        enabled=bool(s.enabled),
        scope_client_id=s.scope_client_id,
        scope_folder_id=s.scope_folder_id,
        platform=s.platform or "all",
        channels=channels,
        email_recipients=_jlist(getattr(s, "email_recipients", None), []),
        day=s.day or "daily",
        send_time=s.send_time or "10:00",
        period_days=int(s.period_days or 7),
        report_format=s.report_format or "desktop",
        include_dynamics=bool(s.include_dynamics),
        approval_required=bool(getattr(s, "approval_required", True)),
        include_ai_comment=bool(getattr(s, "include_ai_comment", True)),
        sections=_jlist(getattr(s, "sections", None), ["kpi", "chart", "channels", "campaigns"]),
        chart_metrics=_jlist(getattr(s, "chart_metrics", None), ["cost", "clicks"]),
        dynamics_metrics=_jlist(getattr(s, "dynamics_metrics", None), ["cost"]),
        chat_targets=_jlist(getattr(s, "chat_targets", None), []),
        scope_label=_schedule_scope_label(db, s),
        last_sent_at=s.last_sent_at,
        created_at=s.created_at,
    )


def _jlist(raw, default=None):
    import json as _json
    if default is None:
        default = []
    try:
        val = _json.loads(raw) if isinstance(raw, str) and raw else raw
        return val if isinstance(val, list) else default
    except Exception:
        return default


def _dump_list(value) -> str:
    import json as _json
    return _json.dumps([str(v) for v in (value or [])])


def _dump_emails(value) -> str:
    normalized = dict.fromkeys(str(item).strip().lower() for item in (value or []) if str(item).strip())
    return _dump_list(normalized.keys())


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except Exception:
        raise HTTPException(status_code=422, detail="Дата должна быть в формате YYYY-MM-DD")


def _scope_filter(query, *, user_id, client_id=None, folder_id=None):
    query = query.filter(models.ReportSchedule.user_id == user_id)
    if folder_id:
        query = query.filter(models.ReportSchedule.scope_folder_id == folder_id)
    elif client_id:
        query = query.filter(models.ReportSchedule.scope_client_id == client_id)
    else:
        query = query.filter(models.ReportSchedule.scope_client_id.is_(None), models.ReportSchedule.scope_folder_id.is_(None))
    return query


def _assert_scope_access(db: Session, user_id, client_id=None, folder_id=None) -> None:
    if client_id and folder_id:
        raise HTTPException(status_code=422, detail="Выберите проект или папку, но не оба сразу")
    if client_id:
        ok = db.query(models.Client.id).filter(models.Client.id == client_id, models.Client.owner_id == user_id).first()
        if not ok:
            raise HTTPException(status_code=404, detail="Проект не найден")
    if folder_id:
        ok = db.query(models.Folder.id).filter(models.Folder.id == folder_id, models.Folder.account_id == user_id).first()
        if not ok:
            raise HTTPException(status_code=404, detail="Папка не найдена")


def _delivery_succeeded(results: Optional[dict]) -> bool:
    from backend_api.reports.scheduler import _delivery_succeeded as succeeded
    return succeeded(results)


def _delivery_approver_name(db: Session, d: models.ReportDelivery) -> Optional[str]:
    """Человекочитаемое имя утвердившего. None → отправлено автоматически."""
    if not d.approved_by_user_id:
        return None
    u = db.query(models.User).filter(models.User.id == d.approved_by_user_id).first()
    if not u:
        return None
    parts = [p for p in [(u.first_name or "").strip(), (u.last_name or "").strip()] if p]
    if parts:
        return " ".join(parts)
    return (u.username or "").strip() or (u.email or "").split("@", 1)[0] or None


def _delivery_scope_label(db: Session, d: models.ReportDelivery) -> str:
    if d.folder_id:
        folder = db.query(models.Folder).filter(models.Folder.id == d.folder_id).first()
        return f"Папка «{folder.name}»" if folder else "Папка"
    if d.client_id:
        client = db.query(models.Client).filter(models.Client.id == d.client_id).first()
        return f"Проект «{client.name}»" if client else "Проект"
    return "Все проекты"


def _delivery_to_response(
    db: Session,
    d: models.ReportDelivery,
    *,
    client_names: Optional[dict] = None,
    folder_names: Optional[dict] = None,
    approver_names: Optional[dict] = None,
) -> schemas.ReportDeliveryResponse:
    if d.folder_id and folder_names is not None:
        scope_label = f"Папка «{folder_names.get(d.folder_id)}»" if folder_names.get(d.folder_id) else "Папка"
    elif d.client_id and client_names is not None:
        scope_label = f"Проект «{client_names.get(d.client_id)}»" if client_names.get(d.client_id) else "Проект"
    elif client_names is not None or folder_names is not None:
        scope_label = "Все проекты"
    else:
        scope_label = _delivery_scope_label(db, d)
    approver_name = approver_names.get(d.approved_by_user_id) if approver_names is not None and d.approved_by_user_id else (
        _delivery_approver_name(db, d) if approver_names is None else None
    )
    return schemas.ReportDeliveryResponse(
        id=d.id,
        status=d.status,
        source=d.source,
        client_id=d.client_id,
        folder_id=d.folder_id,
        schedule_id=d.schedule_id,
        scope_label=scope_label,
        platform=d.platform or "all",
        start_date=d.start_date.isoformat(),
        end_date=d.end_date.isoformat(),
        channels=_jlist(d.channels),
        email_recipients=_jlist(getattr(d, "email_recipients", None)),
        chat_targets=_jlist(d.chat_targets),
        chat_target_details=(d.snapshot_data or {}).get("delivery_targets") or [],
        report_format=d.report_format or "desktop",
        include_dynamics=bool(d.include_dynamics),
        include_ai_comment=bool(d.include_ai_comment),
        sections=_jlist(d.sections, ["kpi", "chart", "channels", "campaigns"]),
        chart_metrics=_jlist(d.chart_metrics, ["cost", "clicks"]),
        dynamics_metrics=_jlist(d.dynamics_metrics, ["cost"]),
        comment=d.comment,
        anomaly_reason=d.anomaly_reason,
        delivery_results=d.delivery_results,
        approved_by_name=approver_name,
        approved_at=d.approved_at,
        sent_at=d.sent_at,
        created_at=d.created_at,
    )


def _refresh_delivery_comment_snapshot(d: models.ReportDelivery) -> None:
    """Обновляет комментарий в файлах, сохраняя исходные цифры снимка."""
    if not d.snapshot_data:
        return
    from backend_api.reports.pdf_service import generate_report_pdf_from_snapshot
    from backend_api.reports.export_service import pdf_first_page_png
    snapshot = dict(d.snapshot_data)
    snapshot["ai_comment"] = (d.comment or "").strip()
    d.snapshot_data = snapshot
    d.pdf_snapshot = generate_report_pdf_from_snapshot(snapshot, d.comment)
    try:
        d.png_snapshot = pdf_first_page_png(d.pdf_snapshot)
    except Exception as exc:
        logger.warning("Delivery %s PNG refresh skipped: %s", d.id, exc)


def _default_project_settings_response(db: Session, current_user: models.User, client_id=None, folder_id=None):
    targets_query = (
        db.query(models.ReportChatTarget)
        .filter(models.ReportChatTarget.user_id == current_user.id)
    )
    if folder_id:
        targets_query = targets_query.filter(models.ReportChatTarget.folder_id == folder_id)
    elif client_id:
        targets_query = targets_query.filter(models.ReportChatTarget.client_id == client_id)
    else:
        targets_query = targets_query.filter(
            models.ReportChatTarget.client_id.is_(None), models.ReportChatTarget.folder_id.is_(None)
        )
    targets = targets_query.order_by(models.ReportChatTarget.created_at).all()
    connected = []
    if (current_user.report_telegram_chat_id or "").strip():
        connected.append("telegram")
    if (getattr(current_user, "report_max_chat_id", None) or getattr(current_user, "report_max_user_id", None) or ""):
        connected.append("max")
    return schemas.ReportProjectSettingsResponse(
        id=None,
        enabled=False,
        scope_client_id=client_id,
        scope_folder_id=folder_id,
        platform="all",
        channels=[],
        email_recipients=[],
        day="daily",
        send_time="10:00",
        period_days=7,
        report_format="desktop",
        include_dynamics=False,
        approval_required=True,
        include_ai_comment=True,
        sections=["kpi", "chart", "channels", "campaigns"],
        chart_metrics=["cost", "clicks"],
        dynamics_metrics=["cost"],
        chat_targets=[],
        scope_label="Проект" if client_id else ("Папка" if folder_id else "Все проекты"),
        connected_channels=connected,
        available_chat_targets=targets,
    )


@router.get("/project-settings", response_model=schemas.ReportProjectSettingsResponse)
def get_project_report_settings(
    client_id: Optional[uuid.UUID] = Query(None),
    folder_id: Optional[uuid.UUID] = Query(None),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    _assert_scope_access(db, current_user.id, client_id=client_id, folder_id=folder_id)
    s = _scope_filter(
        db.query(models.ReportSchedule),
        user_id=current_user.id,
        client_id=client_id,
        folder_id=folder_id,
    ).order_by(models.ReportSchedule.created_at.desc()).first()
    base = _default_project_settings_response(db, current_user, client_id=client_id, folder_id=folder_id)
    if not s:
        return base
    resp = _schedule_to_response(db, s).model_dump()
    resp["connected_channels"] = base.connected_channels
    resp["available_chat_targets"] = base.available_chat_targets
    return schemas.ReportProjectSettingsResponse(**resp)


@router.put("/project-settings", response_model=schemas.ReportProjectSettingsResponse)
def save_project_report_settings(
    body: schemas.ReportScheduleUpdate,
    client_id: Optional[uuid.UUID] = Query(None),
    folder_id: Optional[uuid.UUID] = Query(None),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    if not client_id and not folder_id:
        raise HTTPException(status_code=422, detail="Выберите проект или папку для настройки автоотправки")
    _assert_scope_access(db, current_user.id, client_id=client_id, folder_id=folder_id)
    _validate_schedule_payload(
        day=body.day, send_time=body.send_time, channels=body.channels,
        platform=body.platform, period_days=body.period_days, report_format=body.report_format,
        sections=body.sections, chart_metrics=body.chart_metrics,
    )
    if body.dynamics_metrics:
        bad = [m for m in body.dynamics_metrics if m not in VALID_CHART_METRICS]
        if bad:
            raise HTTPException(status_code=422, detail=f"Неизвестная метрика динамики: {bad[0]}")
    s = _scope_filter(
        db.query(models.ReportSchedule),
        user_id=current_user.id,
        client_id=client_id,
        folder_id=folder_id,
    ).order_by(models.ReportSchedule.created_at.desc()).first()
    if not s:
        s = models.ReportSchedule(
            user_id=current_user.id,
            scope_client_id=client_id,
            scope_folder_id=folder_id,
            name=None,
        )
        db.add(s)
    next_channels = body.channels if body.channels is not None else _jlist(getattr(s, "channels", None), [])
    next_targets = body.chat_targets if body.chat_targets is not None else _jlist(getattr(s, "chat_targets", None), [])
    next_emails = body.email_recipients if body.email_recipients is not None else _jlist(getattr(s, "email_recipients", None), [])
    next_enabled = bool(body.enabled) if body.enabled is not None else bool(s.enabled)
    if body.chat_targets is not None:
        scoped_check = db.query(models.ReportChatTarget.id).filter(models.ReportChatTarget.user_id == current_user.id)
        if folder_id:
            scoped_check = scoped_check.filter(models.ReportChatTarget.folder_id == folder_id)
        else:
            scoped_check = scoped_check.filter(models.ReportChatTarget.client_id == client_id)
        allowed = {str(row.id) for row in scoped_check.all()}
        if any(str(target) not in allowed for target in body.chat_targets):
            raise HTTPException(status_code=422, detail="Получатель не относится к выбранному проекту")
    if "email" in next_channels and not next_emails:
        raise HTTPException(status_code=422, detail="Добавьте хотя бы один email получателя проекта")
    if next_enabled and not (next_channels or next_targets):
        raise HTTPException(status_code=422, detail="Нельзя включить автоотправку без получателей")
    if body.enabled is not None:
        s.enabled = bool(body.enabled)
    if body.platform is not None:
        s.platform = body.platform
    if body.channels is not None:
        s.channels = _dump_list(body.channels)
    if body.email_recipients is not None:
        s.email_recipients = _dump_emails(body.email_recipients)
    if body.day is not None:
        s.day = body.day
    if body.send_time is not None:
        s.send_time = body.send_time
    if body.period_days is not None:
        s.period_days = int(body.period_days)
    if body.report_format is not None:
        s.report_format = body.report_format
    if body.include_dynamics is not None:
        s.include_dynamics = bool(body.include_dynamics)
    if body.approval_required is not None:
        s.approval_required = bool(body.approval_required)
    if body.include_ai_comment is not None:
        s.include_ai_comment = bool(body.include_ai_comment)
    if body.sections is not None:
        s.sections = _dump_list(body.sections)
    if body.chart_metrics is not None:
        s.chart_metrics = _dump_list(body.chart_metrics)
    if body.dynamics_metrics is not None:
        s.dynamics_metrics = _dump_list(body.dynamics_metrics)
    if body.chat_targets is not None:
        scoped = db.query(models.ReportChatTarget.id).filter(models.ReportChatTarget.user_id == current_user.id)
        if folder_id:
            scoped = scoped.filter(models.ReportChatTarget.folder_id == folder_id)
        elif client_id:
            scoped = scoped.filter(models.ReportChatTarget.client_id == client_id)
        else:
            scoped = scoped.filter(models.ReportChatTarget.client_id.is_(None), models.ReportChatTarget.folder_id.is_(None))
        own = {
            str(r.id)
            for r in scoped.all()
        }
        s.chat_targets = _dump_list([t for t in body.chat_targets if str(t) in own])
    db.commit()
    db.refresh(s)
    return get_project_report_settings(client_id=client_id, folder_id=folder_id, current_user=current_user, db=db)


@router.get("/deliveries", response_model=List[schemas.ReportDeliveryResponse])
def list_report_deliveries(
    status: Optional[str] = Query(None, description="pending | sent | failed | history"),
    client_id: Optional[uuid.UUID] = Query(None),
    folder_id: Optional[uuid.UUID] = Query(None),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(models.ReportDelivery).options(
        defer(models.ReportDelivery.pdf_snapshot),
        defer(models.ReportDelivery.png_snapshot),
    ).filter(models.ReportDelivery.user_id == current_user.id)
    if status:
        if status == "history":
            q = q.filter(models.ReportDelivery.status.in_(["sent", "partial", "failed", "cancelled"]))
        else:
            q = q.filter(models.ReportDelivery.status == status)
    # Скоуп проекта/папки — для жёлтой строки на дашборде конкретного проекта
    if folder_id:
        q = q.filter(models.ReportDelivery.folder_id == folder_id)
    elif client_id:
        q = q.filter(models.ReportDelivery.client_id == client_id)
    rows = q.order_by(models.ReportDelivery.created_at.desc()).limit(100).all()
    client_ids = {row.client_id for row in rows if row.client_id}
    folder_ids = {row.folder_id for row in rows if row.folder_id}
    approver_ids = {row.approved_by_user_id for row in rows if row.approved_by_user_id}
    client_names = {row.id: row.name for row in db.query(models.Client.id, models.Client.name).filter(models.Client.id.in_(client_ids)).all()} if client_ids else {}
    folder_names = {row.id: row.name for row in db.query(models.Folder.id, models.Folder.name).filter(models.Folder.id.in_(folder_ids)).all()} if folder_ids else {}
    approver_names = {}
    if approver_ids:
        for user in db.query(models.User).filter(models.User.id.in_(approver_ids)).all():
            parts = [part for part in [(user.first_name or "").strip(), (user.last_name or "").strip()] if part]
            approver_names[user.id] = " ".join(parts) or (user.username or "").strip() or (user.email or "").split("@", 1)[0]
    return [
        _delivery_to_response(
            db, row, client_names=client_names, folder_names=folder_names, approver_names=approver_names,
        )
        for row in rows
    ]


@router.get("/deliveries/pending-count")
def get_pending_report_delivery_count(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    count = db.query(models.ReportDelivery.id).filter(
        models.ReportDelivery.user_id == current_user.id,
        models.ReportDelivery.status == "pending",
    ).count()
    return {"count": count}


@router.post("/deliveries", response_model=schemas.ReportDeliveryResponse)
async def create_report_delivery(
    body: schemas.ReportDeliveryCreate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    _assert_scope_access(db, current_user.id, client_id=body.client_id, folder_id=body.folder_id)
    _validate_schedule_payload(
        channels=body.channels,
        platform=body.platform,
        period_days=7,
        report_format=body.report_format,
        sections=body.sections,
        chart_metrics=body.chart_metrics,
    )
    start_date = _parse_date(body.start_date)
    end_date = _parse_date(body.end_date)
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="Дата начала не может быть позже даты окончания")
    if not (body.channels or body.chat_targets):
        raise HTTPException(status_code=422, detail="Выберите хотя бы одного получателя")
    if "email" in body.channels and not body.email_recipients:
        raise HTTPException(status_code=422, detail="Добавьте email получателя проекта")
    if body.schedule_id:
        own_schedule = db.query(models.ReportSchedule.id).filter(
            models.ReportSchedule.id == body.schedule_id,
            models.ReportSchedule.user_id == current_user.id,
        ).first()
        if not own_schedule:
            raise HTTPException(status_code=404, detail="Настройка автоотправки не найдена")
    target_query = db.query(models.ReportChatTarget.id).filter(models.ReportChatTarget.user_id == current_user.id)
    if body.folder_id:
        target_query = target_query.filter(models.ReportChatTarget.folder_id == body.folder_id)
    elif body.client_id:
        target_query = target_query.filter(models.ReportChatTarget.client_id == body.client_id)
    else:
        target_query = target_query.filter(models.ReportChatTarget.client_id.is_(None), models.ReportChatTarget.folder_id.is_(None))
    allowed_targets = {str(row.id) for row in target_query.all()}
    if any(str(target) not in allowed_targets for target in body.chat_targets):
        raise HTTPException(status_code=422, detail="Получатель не относится к выбранному проекту")
    comment = (body.comment or "").strip() or None
    if body.include_ai_comment and not comment:
        comment = await _resolve_report_comment(
            ai=True,
            comment=None,
            db=db,
            user_id=current_user.id,
            client_id=body.client_id,
            start_date=body.start_date,
            end_date=body.end_date,
            folder_id=str(body.folder_id) if body.folder_id else None,
        )
    d = models.ReportDelivery(
        user_id=current_user.id,
        schedule_id=body.schedule_id,
        client_id=body.client_id,
        folder_id=body.folder_id,
        status="pending",
        source=body.source,
        platform=body.platform or "all",
        start_date=start_date,
        end_date=end_date,
        channels=_dump_list(body.channels),
        email_recipients=_dump_emails(body.email_recipients),
        chat_targets=_dump_list(body.chat_targets),
        report_format=body.report_format or "desktop",
        include_dynamics=bool(body.include_dynamics),
        include_ai_comment=bool(body.include_ai_comment),
        sections=_dump_list(body.sections),
        chart_metrics=_dump_list(body.chart_metrics),
        dynamics_metrics=_dump_list(body.dynamics_metrics),
        comment=comment,
        anomaly_reason=body.anomaly_reason,
    )
    db.add(d)
    db.flush()
    try:
        from backend_api.reports.scheduler import build_delivery_snapshot
        await build_delivery_snapshot(db, d, current_user)
    except Exception as exc:
        db.rollback()
        logger.exception("Report snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail="Не удалось сформировать снимок отчёта")
    db.commit()
    db.refresh(d)
    return _delivery_to_response(db, d)


@router.get("/deliveries/public/{token}/pdf")
def get_public_delivery_pdf(token: str, db: Session = Depends(get_db)):
    """Стабильная секретная ссылка на зафиксированный PDF (30 дней)."""
    d = db.query(models.ReportDelivery).filter(models.ReportDelivery.public_token == token).first()
    if not d or not d.pdf_snapshot or not d.public_expires_at:
        raise HTTPException(status_code=404, detail="Ссылка недействительна")
    expires = d.public_expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=404, detail="Ссылка истекла")
    return Response(
        content=d.pdf_snapshot,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="report_{d.start_date}_{d.end_date}.pdf"'},
    )


@router.get("/deliveries/{delivery_id}", response_model=schemas.ReportDeliveryResponse)
def get_report_delivery(
    delivery_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    d = db.query(models.ReportDelivery).filter(
        models.ReportDelivery.id == delivery_id,
        models.ReportDelivery.user_id == current_user.id,
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    return _delivery_to_response(db, d)


@router.get("/deliveries/{delivery_id}/preview", response_model=schemas.ReportDeliveryPreview)
def get_report_delivery_preview(
    delivery_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Данные «отчёт глазами клиента» для экрана превью (KPI + топ кампаний)."""
    d = db.query(models.ReportDelivery).filter(
        models.ReportDelivery.id == delivery_id,
        models.ReportDelivery.user_id == current_user.id,
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    snapshot = d.snapshot_data or {}
    summary = snapshot.get("summary") or {}
    top_campaigns = snapshot.get("top_campaigns") or []
    client_name = snapshot.get("client_name")
    if not summary and not top_campaigns:  # совместимость со старыми записями
        try:
            summary, top_campaigns, client_name, _, _, _ = _get_report_data(
                db, current_user.id, d.client_id,
                d.start_date.isoformat(), d.end_date.isoformat(), d.comment,
                folder_id=str(d.folder_id) if d.folder_id else None,
                platform=d.platform or "all",
            )
        except Exception as e:
            logger.warning("Preview data failed for delivery %s: %s", delivery_id, e)
            summary, top_campaigns, client_name = {}, [], None
    from backend_api.reports.export_service import _with_cost_breakdown_vat, _with_channel_vat, _campaign_platform
    cost = _with_cost_breakdown_vat(summary.get("expenses", 0), summary.get("cost_by_platform"), d.platform)
    leads = int(summary.get("leads", 0) or 0)
    cpl = (cost / leads) if leads else float(summary.get("cpa", 0) or 0)
    kpi = schemas.ReportDeliveryPreviewKpi(
        cost=round(cost, 2),
        leads=leads,
        cpl=round(cpl, 2),
        impressions=int(summary.get("impressions", 0) or 0),
        clicks=int(summary.get("clicks", 0) or 0),
    )
    camps = []
    for c in (top_campaigns or [])[:5]:
        camps.append(schemas.ReportDeliveryPreviewCampaign(
            name=str(c.get("name") or c.get("campaign_name") or "—"),
            leads=int(c.get("conversions", 0) or 0),
            cost=round(_with_channel_vat(c.get("cost", 0), _campaign_platform(c)), 2),
        ))
    return schemas.ReportDeliveryPreview(
        scope_label=_delivery_scope_label(db, d),
        client_name=client_name,
        start_date=d.start_date.isoformat(),
        end_date=d.end_date.isoformat(),
        kpi=kpi,
        top_campaigns=camps,
        comment=d.comment,
    )


@router.post("/deliveries/{delivery_id}/regenerate-comment", response_model=schemas.ReportDeliveryResponse)
async def regenerate_delivery_comment(
    delivery_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Пересобрать AI-комментарий отчёта (кнопка «Сгенерировать заново» в превью)."""
    d = db.query(models.ReportDelivery).filter(
        models.ReportDelivery.id == delivery_id,
        models.ReportDelivery.user_id == current_user.id,
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    if d.status not in ("pending", "failed", "partial"):
        raise HTTPException(status_code=422, detail="Этот отчёт уже обработан")
    new_comment = await _resolve_report_comment(
        ai=True, comment=None, db=db, user_id=current_user.id,
        client_id=d.client_id, start_date=d.start_date.isoformat(),
        end_date=d.end_date.isoformat(),
        folder_id=str(d.folder_id) if d.folder_id else None,
    )
    d.comment = (new_comment or "").strip() or None
    _refresh_delivery_comment_snapshot(d)
    db.commit()
    db.refresh(d)
    return _delivery_to_response(db, d)


@router.put("/deliveries/{delivery_id}", response_model=schemas.ReportDeliveryResponse)
def save_report_delivery_draft(
    delivery_id: uuid.UUID,
    body: schemas.ReportDeliveryDraft,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Сохранить отредактированный комментарий без отправки («Сохранить черновик»)."""
    d = db.query(models.ReportDelivery).filter(
        models.ReportDelivery.id == delivery_id,
        models.ReportDelivery.user_id == current_user.id,
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    if d.status not in ("pending", "failed", "partial"):
        raise HTTPException(status_code=422, detail="Этот отчёт уже обработан")
    d.comment = (body.comment or "").strip() or None
    _refresh_delivery_comment_snapshot(d)
    db.commit()
    db.refresh(d)
    return _delivery_to_response(db, d)


@router.post("/deliveries/{delivery_id}/approve", response_model=schemas.ReportDeliveryResponse)
async def approve_report_delivery(
    delivery_id: uuid.UUID,
    body: schemas.ReportDeliveryApprove,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    d = db.query(models.ReportDelivery).filter(
        models.ReportDelivery.id == delivery_id,
        models.ReportDelivery.user_id == current_user.id,
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    if d.status not in ("pending", "failed", "partial"):
        raise HTTPException(status_code=422, detail="Этот отчёт уже обработан")
    claimed_from_status = d.status
    retry_failed_only = d.status in ("failed", "partial") and bool(d.delivery_results)
    if body.comment is not None:
        d.comment = body.comment.strip() or None
        _refresh_delivery_comment_snapshot(d)

    try:
        from backend_api.reports.scheduler import send_report_delivery, delivery_status_from_results
        if not d.approved_by_user_id:
            d.approved_by_user_id = current_user.id
            d.approved_at = datetime.now(timezone.utc)
        db.flush()
        claimed = db.query(models.ReportDelivery).filter(
            models.ReportDelivery.id == d.id,
            models.ReportDelivery.status == claimed_from_status,
        ).update({models.ReportDelivery.status: "sending"}, synchronize_session=False)
        if claimed != 1:
            db.rollback()
            raise HTTPException(status_code=409, detail="Отчёт уже отправляется или обработан")
        d.status = "sending"
        db.commit()
        results = await send_report_delivery(db, d, current_user, retry_failed_only=retry_failed_only)
        d.delivery_results = results
        d.status = delivery_status_from_results(results, _jlist(d.channels), _jlist(d.chat_targets))
        d.sent_at = datetime.now(timezone.utc) if d.status in ("sent", "partial") else None
        if d.schedule_id and d.status in ("sent", "partial"):
            schedule = db.query(models.ReportSchedule).filter(models.ReportSchedule.id == d.schedule_id).first()
            if schedule:
                schedule.last_sent_at = d.sent_at
        db.commit()
        db.refresh(d)
        return _delivery_to_response(db, d)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Report delivery approve failed: %s", e)
        d.status = "failed"
        d.delivery_results = {"errors": {"system": str(e)}}
        db.commit()
        db.refresh(d)
        return _delivery_to_response(db, d)


@router.get("/schedules", response_model=List[schemas.ReportScheduleResponse])
def list_report_schedules(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.ReportSchedule)
        .filter(models.ReportSchedule.user_id == current_user.id)
        .order_by(models.ReportSchedule.created_at)
        .all()
    )
    return [_schedule_to_response(db, s) for s in rows]


@router.post("/schedules", response_model=schemas.ReportScheduleResponse)
def create_report_schedule(
    body: schemas.ReportScheduleCreate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    import json as _json
    if not body.scope_client_id and not body.scope_folder_id:
        raise HTTPException(status_code=422, detail="Автоотправка настраивается только для проекта или папки")
    _assert_scope_access(db, current_user.id, client_id=body.scope_client_id, folder_id=body.scope_folder_id)
    existing = _scope_filter(
        db.query(models.ReportSchedule), user_id=current_user.id,
        client_id=body.scope_client_id, folder_id=body.scope_folder_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="У проекта уже есть настройка автоотправки")
    _validate_schedule_payload(
        day=body.day, send_time=body.send_time, channels=body.channels,
        platform=body.platform, period_days=body.period_days, report_format=body.report_format,
        sections=body.sections, chart_metrics=body.chart_metrics,
    )
    if body.dynamics_metrics:
        bad = [m for m in body.dynamics_metrics if m not in VALID_CHART_METRICS]
        if bad:
            raise HTTPException(status_code=422, detail=f"Неизвестная метрика динамики: {bad[0]}")
    if "email" in body.channels and not body.email_recipients:
        raise HTTPException(status_code=422, detail="Добавьте email получателя проекта")
    if body.enabled and not (body.channels or body.chat_targets):
        raise HTTPException(status_code=422, detail="Выберите, куда отправлять: личный канал или группу")
    scoped_targets = db.query(models.ReportChatTarget.id).filter(models.ReportChatTarget.user_id == current_user.id)
    if body.scope_folder_id:
        scoped_targets = scoped_targets.filter(models.ReportChatTarget.folder_id == body.scope_folder_id)
    else:
        scoped_targets = scoped_targets.filter(models.ReportChatTarget.client_id == body.scope_client_id)
    allowed_target_ids = {str(row.id) for row in scoped_targets.all()}
    if any(str(target) not in allowed_target_ids for target in body.chat_targets):
        raise HTTPException(status_code=422, detail="Получатель не относится к выбранному проекту")
    s = models.ReportSchedule(
        user_id=current_user.id,
        name=(body.name or "").strip() or None,
        enabled=bool(body.enabled),
        scope_client_id=body.scope_client_id,
        scope_folder_id=body.scope_folder_id,
        platform=body.platform or "all",
        channels=_json.dumps(body.channels or []),
        email_recipients=_dump_emails(body.email_recipients),
        day=body.day or "daily",
        send_time=body.send_time or "10:00",
        period_days=int(body.period_days or 7),
        report_format=body.report_format or "desktop",
        include_dynamics=bool(body.include_dynamics),
        approval_required=bool(body.approval_required),
        include_ai_comment=bool(body.include_ai_comment),
        sections=_json.dumps(body.sections or ["kpi", "chart", "channels", "campaigns"]),
        chart_metrics=_json.dumps(body.chart_metrics or ["cost", "clicks"]),
        dynamics_metrics=_json.dumps(body.dynamics_metrics or ["cost"]),
        chat_targets=_json.dumps([str(t) for t in (body.chat_targets or [])]),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _schedule_to_response(db, s)


@router.put("/schedules/{schedule_id}", response_model=schemas.ReportScheduleResponse)
def update_report_schedule(
    schedule_id: uuid.UUID,
    body: schemas.ReportScheduleUpdate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    import json as _json
    s = db.query(models.ReportSchedule).filter(
        models.ReportSchedule.id == schedule_id,
        models.ReportSchedule.user_id == current_user.id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Правило не найдено")
    _assert_scope_access(db, current_user.id, client_id=s.scope_client_id, folder_id=s.scope_folder_id)
    _validate_schedule_payload(
        day=body.day, send_time=body.send_time, channels=body.channels,
        platform=body.platform, period_days=body.period_days, report_format=body.report_format,
        sections=body.sections, chart_metrics=body.chart_metrics,
    )
    if body.name is not None:
        s.name = body.name.strip() or None
    if body.enabled is not None:
        s.enabled = bool(body.enabled)
    # Скоуп: явное поле в PUT перезаписывает (None = «все проекты», поэтому
    # обновляем оба поля вместе, когда хотя бы одно передано)
    if "scope_client_id" in body.model_fields_set or "scope_folder_id" in body.model_fields_set:
        if not body.scope_client_id and not body.scope_folder_id:
            raise HTTPException(status_code=422, detail="Автоотправка настраивается только для проекта или папки")
        _assert_scope_access(
            db, current_user.id,
            client_id=body.scope_client_id, folder_id=body.scope_folder_id,
        )
        duplicate = _scope_filter(
            db.query(models.ReportSchedule), user_id=current_user.id,
            client_id=body.scope_client_id, folder_id=body.scope_folder_id,
        ).filter(models.ReportSchedule.id != s.id).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="У проекта уже есть настройка автоотправки")
        s.scope_client_id = body.scope_client_id
        s.scope_folder_id = body.scope_folder_id
    if body.platform is not None:
        s.platform = body.platform
    if body.channels is not None:
        s.channels = _json.dumps(body.channels)
    if body.email_recipients is not None:
        s.email_recipients = _dump_emails(body.email_recipients)
    if body.day is not None:
        s.day = body.day
    if body.send_time is not None:
        s.send_time = body.send_time
    if body.period_days is not None:
        s.period_days = int(body.period_days)
    if body.report_format is not None:
        s.report_format = body.report_format
    if body.include_dynamics is not None:
        s.include_dynamics = bool(body.include_dynamics)
    if body.approval_required is not None:
        s.approval_required = bool(body.approval_required)
    if body.include_ai_comment is not None:
        s.include_ai_comment = bool(body.include_ai_comment)
    if body.sections is not None:
        s.sections = _json.dumps(body.sections)
    if body.chart_metrics is not None:
        s.chart_metrics = _json.dumps(body.chart_metrics)
    if body.dynamics_metrics is not None:
        bad = [m for m in body.dynamics_metrics if m not in VALID_CHART_METRICS]
        if bad:
            raise HTTPException(status_code=422, detail=f"Неизвестная метрика динамики: {bad[0]}")
        s.dynamics_metrics = _json.dumps(body.dynamics_metrics)
    if body.chat_targets is not None:
        scoped = db.query(models.ReportChatTarget.id).filter(models.ReportChatTarget.user_id == current_user.id)
        if s.scope_folder_id:
            scoped = scoped.filter(models.ReportChatTarget.folder_id == s.scope_folder_id)
        elif s.scope_client_id:
            scoped = scoped.filter(models.ReportChatTarget.client_id == s.scope_client_id)
        own = {
            str(r.id)
            for r in scoped.all()
        }
        s.chat_targets = _json.dumps([str(t) for t in body.chat_targets if str(t) in own])
    next_channels = _jlist(s.channels, [])
    next_targets = _jlist(s.chat_targets, [])
    next_emails = _jlist(s.email_recipients, [])
    if "email" in next_channels and not next_emails:
        raise HTTPException(status_code=422, detail="Добавьте email получателя проекта")
    if s.enabled and not (next_channels or next_targets):
        raise HTTPException(status_code=422, detail="Нельзя включить автоотправку без получателей")
    db.commit()
    db.refresh(s)
    return _schedule_to_response(db, s)


@router.delete("/schedules/{schedule_id}")
def delete_report_schedule(
    schedule_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    s = db.query(models.ReportSchedule).filter(
        models.ReportSchedule.id == schedule_id,
        models.ReportSchedule.user_id == current_user.id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Правило не найдено")
    db.delete(s)
    db.commit()
    return {"ok": True}


@router.post("/schedules/{schedule_id}/test")
async def test_report_schedule(
    schedule_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Отправить отчёт по правилу прямо сейчас (проверка настройки)."""
    s = db.query(models.ReportSchedule).filter(
        models.ReportSchedule.id == schedule_id,
        models.ReportSchedule.user_id == current_user.id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Правило не найдено")
    from backend_api.reports.scheduler import (
        create_pending_delivery_for_schedule, build_delivery_snapshot,
        send_report_delivery, delivery_status_from_results,
    )
    delivery = create_pending_delivery_for_schedule(db, s, source="manual")
    db.flush()
    await build_delivery_snapshot(db, delivery, current_user)
    results = await send_report_delivery(db, delivery, current_user)
    delivery.delivery_results = results
    delivery.status = delivery_status_from_results(results, _jlist(delivery.channels), _jlist(delivery.chat_targets))
    delivery.sent_at = datetime.now(timezone.utc) if delivery.status in ("sent", "partial") else None
    s.last_sent_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": delivery.status == "sent", "status": delivery.status, "results": results}


# ══════════ Групповые чаты для отчётов (бот в группе TG/MAX) ══════════

@router.get("/chat-targets", response_model=List[schemas.ReportChatTargetResponse])
def list_chat_targets(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.ReportChatTarget)
        .filter(models.ReportChatTarget.user_id == current_user.id)
        .order_by(models.ReportChatTarget.created_at)
        .all()
    )
    return rows


@router.post("/chat-targets/link-code")
async def create_chat_target_link_code(
    body: dict,
    client_id: Optional[uuid.UUID] = Query(None),
    folder_id: Optional[uuid.UUID] = Query(None),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Код для подключения ГРУППЫ: пользователь добавляет бота в группу и отправляет
    там «/link <код>» — webhook сохраняет chat_id группы как цель доставки отчётов."""
    import secrets as _secrets
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    kind = str((body or {}).get("kind") or "").lower()
    target_type = str((body or {}).get("target_type") or "group").lower()
    if kind not in ("telegram", "max"):
        raise HTTPException(status_code=422, detail="kind: telegram или max")
    if target_type not in ("group", "client"):
        raise HTTPException(status_code=422, detail="target_type: group или client")
    if not client_id and not folder_id:
        raise HTTPException(status_code=422, detail="Ссылка получателя должна относиться к проекту или папке")
    _assert_scope_access(db, current_user.id, client_id=client_id, folder_id=folder_id)
    code = _secrets.token_urlsafe(8)[:12]
    expires = _dt.now(_tz.utc) + _td(minutes=30)
    if kind == "telegram":
        db.add(models.TelegramLinkToken(
            user_id=current_user.id, client_id=client_id, folder_id=folder_id,
            target_type=target_type, token=code, expires_at=expires,
        ))
    else:
        db.add(models.MaxReportLinkToken(
            user_id=current_user.id, client_id=client_id, folder_id=folder_id,
            target_type=target_type, token=code, expires_at=expires,
        ))
    db.commit()
    bot_hint = ""
    group_link = None
    try:
        if kind == "telegram":
            from backend_api.telegram_report_link import _resolve_bot_username
            bot_hint = await _resolve_bot_username()
            # Deep-link: открывает выбор группы и сам отправляет /start <код> в неё —
            # привязка происходит автоматически, команду руками писать не нужно
            group_link = (
                f"https://t.me/{bot_hint}?startgroup={code}"
                if target_type == "group"
                else f"https://t.me/{bot_hint}?start={code}"
            )
        else:
            from backend_api.services.max_reports_bot import resolve_bot_name
            bot_hint = await resolve_bot_name()
            if target_type == "client":
                group_link = f"https://max.ru/{bot_hint}?start={code}"
    except Exception as e:
        import logging as _logging
        _logging.getLogger(__name__).warning("link-code bot resolve failed: %s", e)
    return {
        "code": code,
        "command": f"/link {code}",
        "bot": bot_hint,
        "group_link": group_link,
        "target_type": target_type,
        "expires_in_minutes": 30,
    }


@router.delete("/chat-targets/{target_id}")
def delete_chat_target(
    target_id: uuid.UUID,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(models.ReportChatTarget).filter(
        models.ReportChatTarget.id == target_id,
        models.ReportChatTarget.user_id == current_user.id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Чат не найден")
    target_id_text = str(row.id)
    for schedule in db.query(models.ReportSchedule).filter(models.ReportSchedule.user_id == current_user.id).all():
        target_ids = [str(value) for value in _jlist(schedule.chat_targets, [])]
        if target_id_text in target_ids:
            schedule.chat_targets = _dump_list([value for value in target_ids if value != target_id_text])
    db.delete(row)
    db.commit()
    return {"ok": True}
