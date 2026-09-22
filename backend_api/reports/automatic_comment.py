"""One paid attempt per immutable automatic delivery, detached IO/render.

An unknown generation is not automatically repeated on a delivery retry.
Human edits/settings changes while the model/render runs win over its output.
"""
from copy import deepcopy
from datetime import datetime, timedelta
from types import SimpleNamespace
import hashlib
import json
import logging
import uuid
import sqlalchemy as sa
from core import models

logger = logging.getLogger(__name__)


class AutomaticCommentPending(RuntimeError):
    """Another request is generating this report; do not send a different file."""


def revision(delivery):
    fields = ('user_id', 'client_id', 'folder_id', 'start_date', 'end_date', 'platform',
              'snapshot_data', 'comment', 'comment_status', 'include_ai_comment', 'source',
              'channels', 'chat_targets', 'email_recipients', 'report_format', 'include_dynamics',
              'sections', 'chart_metrics', 'dynamics_metrics', 'approved_by_user_id', 'approved_at')
    return hashlib.sha256(json.dumps({name: getattr(delivery, name, None) for name in fields},
        default=str, sort_keys=True).encode()).hexdigest()


def locked(db, delivery_id):
    return db.scalar(sa.select(models.ReportDelivery).where(models.ReportDelivery.id == delivery_id)
        .execution_options(populate_existing=True).with_for_update())


async def generate(db, delivery, user_id):
    from ai.report_generator import generate_delivery_comment
    from backend_api.reports.scheduler import refresh_delivery_snapshot_files
    # Caller owns this workflow transaction; persist the prepared snapshot first.
    db.flush()
    delivery_id = delivery.id
    row = locked(db, delivery_id)
    if row is None or row.user_id != user_id:
        raise ValueError('Automatic report owner changed')
    results = dict(row.delivery_results or {})
    if (row.source != 'auto' or not row.include_ai_comment or (row.comment or '').strip()
            or row.comment_status in {'edited', 'approved'} or row.approved_at):
        db.commit()
        return
    previous = results.get('automatic_ai_attempt')
    now = db.scalar(sa.select(sa.func.clock_timestamp()))
    if previous:
        if previous.get('status') == 'sending':
            deadline = datetime.fromisoformat(previous['deadline']) if previous.get('deadline') else None
            if deadline is None or now < deadline:
                raise AutomaticCommentPending('AI-комментарий отчёта ещё готовится. Повторите проверку позже.')
            row.delivery_results = {**results, 'automatic_ai_attempt': {**previous,
                'status': 'uncertain', 'error_type': 'GenerationDeadlineExceeded'}}
        db.commit()
        return
    if not row.snapshot_data or (row.data_readiness or {}).get('status') != 'ready':
        raise ValueError('Automatic comment requires a ready immutable delivery')
    proof = revision(row)
    detached = SimpleNamespace(**{c.key: deepcopy(getattr(row, c.key)) for c in models.ReportDelivery.__table__.columns})
    attempt = {'id': str(uuid.uuid4()), 'status': 'sending', 'snapshot': proof,
               'deadline': (now + timedelta(minutes=5)).isoformat()}
    row.delivery_results = {**results, 'automatic_ai_attempt': attempt}
    db.commit()
    try:
        text = (await generate_delivery_comment(deepcopy(detached.snapshot_data)) or '').strip()
        if not text:
            raise ValueError('Automatic comment is empty')
        detached.comment, detached.comment_status = text, 'draft'
        refresh_delivery_snapshot_files(detached)  # PDF/PNG: zero SQL connections.
    except Exception as exc:
        # Do not log prompts, provider response bodies, or customer data.
        row = locked(db, delivery_id)
        if row and (row.delivery_results or {}).get('automatic_ai_attempt') == attempt:
            row.delivery_results = {**row.delivery_results,
                'automatic_ai_attempt': {**attempt, 'status': 'uncertain', 'error_type': type(exc).__name__}}
            db.commit()
        logger.warning('Automatic report comment unavailable: %s', type(exc).__name__)
        return
    row = locked(db, delivery_id)
    if row is None:
        db.rollback()
        return
    if (row.delivery_results or {}).get('automatic_ai_attempt') != attempt:
        db.rollback()
        return
    expired = db.scalar(sa.select(sa.func.clock_timestamp())) >= datetime.fromisoformat(attempt['deadline'])
    status = 'uncertain' if expired else 'superseded'
    if not expired and revision(row) == proof:
        for name in ('comment', 'comment_status', 'snapshot_data', 'pdf_snapshot', 'png_snapshot'):
            setattr(row, name, getattr(detached, name))
        status = 'confirmed'
    row.delivery_results = {**row.delivery_results, 'automatic_ai_attempt': {**attempt, 'status': status}}
    db.commit()
