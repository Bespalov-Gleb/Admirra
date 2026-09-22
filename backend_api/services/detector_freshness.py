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


def status(db, client_id, ref=None, *, refresh=False):
    if not consumer_freshness.enabled("detector"):
        return None
    try:
        return evidence(db, client_id, ref)
    except DataNotReady as exc:
        result = {"status": "waiting_data", "reason": exc.reason}
        if getattr(exc, "refresh_scope", None):
            from automation.consumer_refresh import request, lookup
            client = db.get(models.Client, client_id)
            result["refresh"] = (request(db, "detector", client.owner_id, *exc.refresh_scope) if refresh else
                lookup(db, "detector", client.owner_id, exc.refresh_scope, exc.refresh_requirements))
        return result


def pending(db, client_id, ref=None):
    proof = status(db, client_id, ref)
    return proof is not None and proof["status"] != "ready"


def issue(proof=None):
    refresh = (proof or {}).get("refresh")
    return {"channel": "all", "days": None, "status": "no_data", "data_readiness": refresh,
        "text": refresh["message"] if refresh else "Полнота данных не подтверждена. Обновите данные проекта; выводы детектора пока недоступны."}
