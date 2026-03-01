from fastapi import APIRouter, Depends

from middleware.auth import get_site
from models.database import SessionLocal, Site
from services.plans import get_plan_config, get_usage_count

router = APIRouter()


@router.get("/usage")
def get_usage(site: Site = Depends(get_site)):
    db = SessionLocal()
    try:
        # Re-fetch site so SQLAlchemy tracks any mutations (e.g. period_start reset)
        site = db.query(Site).filter(Site.id == site.id).first()

        config = get_plan_config(site.plan)

        if config["unlimited"]:
            return {
                "plan": site.plan,
                "limit": None,
                "used": None,
                "remaining": None,
                "resets_monthly": False,
            }

        used, was_reset = get_usage_count(site, db)
        if was_reset:
            db.commit()

        return {
            "plan": site.plan,
            "limit": site.message_limit,
            "used": used,
            "remaining": max(0, site.message_limit - used),
            "resets_monthly": config["resets_monthly"],
        }
    finally:
        db.close()
