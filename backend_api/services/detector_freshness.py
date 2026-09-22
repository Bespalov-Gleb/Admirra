"""Coverage barrier for detector-derived decisions (not a new alert lifecycle)."""
from datetime import date, timedelta
from core import consumer_freshness, models
from core.config import get_config
from core.data_requirements import DataNotReady


def evidence(db, client_id, ref=None):
    ref = ref or date.today()
    cfg = get_config().detector
    days = max(cfg.baseline_days + cfg.fresh_window_days + cfg.fresh_window_skip_days,
        2 * cfg.plan_cpl_window_days, cfg.balance_spend_window_days, cfg.balance_zero_history_days,
        cfg.stopped_spend_zero_days + cfg.stopped_prior_spend_days,
        cfg.tracking_zero_leads_days + cfg.tracking_history_days, 14)
    first = ref - timedelta(days=days)
    # Active plan fact/forecast starts at the plan date, possibly before baseline.
    for model in (models.ProjectBudget, models.ProjectTargetCPA):
        start = db.query(model.period_start).filter(model.client_id == client_id,
            model.period_start <= ref, model.period_end >= ref).order_by(model.period_start).first()
        if start:
            first = min(first, start[0])
    return consumer_freshness.verify(db, [client_id], first, ref)


def status(db, client_id, ref=None):
    if not consumer_freshness.enabled("detector"):
        return None
    try:
        return evidence(db, client_id, ref)
    except DataNotReady as exc:
        return {"status": "waiting_data", "reason": exc.reason}


def pending(db, client_id, ref=None):
    proof = status(db, client_id, ref)
    return proof is not None and proof["status"] != "ready"


def issue():
    return {"channel": "all", "days": None, "status": "no_data",
        "text": "Ожидаем полные данные синхронизации. Выводы детектора временно недоступны."}
