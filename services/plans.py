import datetime
from datetime import timezone

from sqlalchemy import func

from models.database import RequestLog

PLAN_CONFIG = {
    "free":       {"limit": 20,   "resets_monthly": False, "unlimited": False, "chunk_limit": 250},
    "pro":        {"limit": 2000, "resets_monthly": True,  "unlimited": False, "chunk_limit": 10_000},
    "enterprise": {"limit": None, "resets_monthly": False, "unlimited": True,  "chunk_limit": None},
}


def get_plan_config(plan: str) -> dict:
    if plan not in PLAN_CONFIG:
        raise ValueError(f"Unknown plan: {plan!r}. Valid plans: {list(PLAN_CONFIG)}")
    return PLAN_CONFIG[plan]


def get_usage_count(site, db) -> tuple:
    """Return (used, was_reset). Mutates site.period_start for pro resets."""
    config = get_plan_config(site.plan)

    if config["unlimited"]:
        return (0, False)

    if site.plan == "pro":
        now = datetime.datetime.now(timezone.utc)
        was_reset = False
        if site.period_start is None or (now - site.period_start).days >= 30:
            site.period_start = now
            was_reset = True
        used = db.query(func.count(RequestLog.id)).filter(
            RequestLog.site_id == site.id,
            RequestLog.endpoint == "/chat",
            RequestLog.status_code == 200,
            RequestLog.created_at >= site.period_start,
        ).scalar()
        return (used, was_reset)

    # free — all-time count
    used = db.query(func.count(RequestLog.id)).filter(
        RequestLog.site_id == site.id,
        RequestLog.endpoint == "/chat",
        RequestLog.status_code == 200,
    ).scalar()
    return (used, False)
