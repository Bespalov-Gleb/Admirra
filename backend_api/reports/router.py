"""
Роутер отчётов: PDF, отправка в Email и Telegram.
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
from backend_api.reports.pdf_service import generate_report_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])


class SendReportRequest(BaseModel):
    report_type: str = "ai"  # pdf | ai | text
    channels: List[str]  # ["email", "telegram"]
    email_recipients: Optional[List[str]] = None
    telegram_chat_id: Optional[str] = None
    client_id: Optional[str] = None
    start_date: str
    end_date: str
    comment: Optional[str] = None  # готовый текст — если передан, не генерируем заново


@router.get("/pdf")
async def get_report_pdf(
    start_date: str = Query(...),
    end_date: str = Query(...),
    client_id: Optional[str] = Query(None),
    ai: bool = Query(False, description="Генерировать отчёт с ИИ"),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Скачивание PDF-отчёта за указанный период. При ai=true — с AI-комментарием.
    """
    u_client_id = None
    if client_id:
        try:
            u_client_id = uuid.UUID(client_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный client_id")

    comment = None
    if ai:
        try:
            logger.info("PDF report: generating AI comment (ai=true)")
            from ai.report_generator import generate_report
            comment = await generate_report(
                db=db,
                user_id=current_user.id,
                client_id=u_client_id,
                start_date=start_date,
                end_date=end_date,
                report_type="full",
            )
            if not comment or not str(comment).strip():
                logger.warning("PDF report: AI returned empty comment, using fallback")
                comment = "AI не удалось сформировать комментарий. Проверьте настройки OPENAI_API_KEY в .env и доступность API."
            else:
                logger.info("PDF report: AI comment received, length=%d", len(str(comment)))
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
            comment=comment,
        )
        filename = f"report_{start_date}_{end_date}.pdf"
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
    ai_text = None

    # Если передан готовый текст — используем его напрямую, не генерируем заново
    if req.comment and req.comment.strip():
        ai_text = req.comment.strip()
        logger.info("send_report: using provided comment text (len=%d), skipping AI generation", len(ai_text))
    elif req.report_type == "pdf":
        try:
            pdf_bytes = generate_report_pdf(
                db=db,
                user_id=current_user.id,
                client_id=u_client_id,
                start_date=req.start_date,
                end_date=req.end_date,
                comment=None,
            )
        except Exception as e:
            logger.exception("PDF generation failed: %s", e)
            raise HTTPException(status_code=500, detail="Не удалось сформировать PDF")
    elif req.report_type in ("ai", "text"):
        try:
            from ai.report_generator import generate_report
            ai_text = await generate_report(
                db=db,
                user_id=current_user.id,
                client_id=u_client_id,
                start_date=req.start_date,
                end_date=req.end_date,
                report_type="full",
            )
        except Exception as e:
            logger.exception("AI report generation failed: %s", e)
            raise HTTPException(status_code=500, detail="Не удалось сформировать AI-отчёт")

    results = {"email": False, "telegram": False, "email_error": None}

    # Email
    if "email" in req.channels and req.email_recipients:
        try:
            from lead_validator.services.email_sender import email_sender
            subject = f"Отчёт за период {req.start_date} — {req.end_date}"
            body_text = ai_text if ai_text else f"Отчёт по рекламным кампаниям за период {req.start_date} — {req.end_date}."
            if pdf_bytes:
                ok, err = await email_sender.send_report_email(
                    recipients=req.email_recipients,
                    subject=subject,
                    body=body_text,
                    pdf_bytes=pdf_bytes,
                    filename=f"report_{req.start_date}_{req.end_date}.pdf",
                )
            else:
                ok, err = await email_sender.send_report_email(
                    recipients=req.email_recipients,
                    subject=subject,
                    body=body_text,
                )
            results["email"] = ok
            if err:
                results["email_error"] = err
        except ImportError:
            raise HTTPException(status_code=503, detail="Модуль email недоступен")
        except Exception as e:
            logger.exception("Email send failed: %s", e)
            results["email_error"] = str(e)

    # Telegram
    if "telegram" in req.channels and req.telegram_chat_id:
        if pdf_bytes:
            try:
                from lead_validator.services.telegram import telegram_notifier
                caption = f"Отчёт за период {req.start_date} — {req.end_date}"
                results["telegram"] = await telegram_notifier.send_document(
                    chat_id=req.telegram_chat_id,
                    document=pdf_bytes,
                    filename=f"report_{req.start_date}_{req.end_date}.pdf",
                    caption=caption,
                )
            except ImportError:
                raise HTTPException(status_code=503, detail="Модуль Telegram недоступен")
            except Exception as e:
                logger.exception("Telegram send failed: %s", e)
        elif ai_text:
            try:
                from lead_validator.services.telegram import telegram_notifier
                header = f"📊 AI-отчёт за период {req.start_date} — {req.end_date}\n\n"
                results["telegram"] = await telegram_notifier.send_message(
                    text=header + ai_text,
                    parse_mode=None,
                    chat_id=req.telegram_chat_id,
                )
            except ImportError:
                raise HTTPException(status_code=503, detail="Модуль Telegram недоступен")
            except Exception as e:
                logger.exception("Telegram send failed: %s", e)
        else:
            raise HTTPException(status_code=400, detail="Нет данных для отправки в Telegram")

    return {"ok": True, "results": results}
