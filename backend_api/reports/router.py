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
    report_type: str = "pdf"  # pdf | text
    channels: List[str]  # ["email", "telegram"]
    email_recipients: Optional[List[str]] = None
    telegram_chat_id: Optional[str] = None
    client_id: Optional[str] = None
    start_date: str
    end_date: str


@router.get("/pdf")
async def get_report_pdf(
    start_date: str = Query(...),
    end_date: str = Query(...),
    client_id: Optional[str] = Query(None),
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Скачивание PDF-отчёта за указанный период.
    """
    u_client_id = None
    if client_id:
        try:
            u_client_id = uuid.UUID(client_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный client_id")

    try:
        pdf_bytes = generate_report_pdf(
            db=db,
            user_id=current_user.id,
            client_id=u_client_id,
            start_date=start_date,
            end_date=end_date,
            comment=None,
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
    if req.report_type == "pdf":
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

    results = {"email": False, "telegram": False}

    # Email
    if "email" in req.channels and req.email_recipients:
        try:
            from lead_validator.services.email_sender import email_sender
            subject = f"Отчёт за период {req.start_date} — {req.end_date}"
            body_text = f"Отчёт по рекламным кампаниям за период {req.start_date} — {req.end_date}."
            if pdf_bytes:
                results["email"] = await email_sender.send_report_email(
                    recipients=req.email_recipients,
                    subject=subject,
                    body=body_text,
                    pdf_bytes=pdf_bytes,
                    filename=f"report_{req.start_date}_{req.end_date}.pdf",
                )
            else:
                results["email"] = await email_sender.send_report_email(
                    recipients=req.email_recipients,
                    subject=subject,
                    body=body_text,
                )
        except ImportError:
            raise HTTPException(status_code=503, detail="Модуль email недоступен")
        except Exception as e:
            logger.exception("Email send failed: %s", e)

    # Telegram
    if "telegram" in req.channels and req.telegram_chat_id:
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="Для Telegram нужен PDF")
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

    return {"ok": True, "results": results}
