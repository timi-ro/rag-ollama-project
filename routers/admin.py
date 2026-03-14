import datetime
from datetime import timezone
import secrets
import bcrypt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from typing import Optional

from middleware.auth import get_admin
from models.database import SessionLocal, Site, RequestLog
from services.plans import get_plan_config
from services.vectorstore import delete_site_chunks

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateSiteRequest(BaseModel):
    name: str
    plan: str = "free"


class UpdateSiteRequest(BaseModel):
    plan: Optional[str] = None
    is_active: Optional[bool] = None


@router.post("/sites")
def create_site(req: CreateSiteRequest, _=Depends(get_admin)):
    try:
        config = get_plan_config(req.plan)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    raw_key = secrets.token_urlsafe(32)
    key_hash = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
    period_start = datetime.datetime.now(timezone.utc) if config["resets_monthly"] else None

    db = SessionLocal()
    try:
        if db.query(Site).filter(Site.name == req.name).first():
            raise HTTPException(status_code=409, detail=f"A site named '{req.name}' already exists.")
        site = Site(
            name=req.name,
            api_key_prefix=raw_key[:8],
            api_key_hash=key_hash,
            plan=req.plan,
            message_limit=config["limit"],
            period_start=period_start,
        )
        db.add(site)
        db.commit()
        db.refresh(site)
        return {
            "site_id": site.id,
            "name": site.name,
            "api_key": raw_key,
            "plan": site.plan,
            "message_limit": config["limit"],
        }
    finally:
        db.close()


@router.get("/sites")
def list_sites(_=Depends(get_admin)):
    db = SessionLocal()
    try:
        sites = db.query(Site).all()
        result = []
        for site in sites:
            total = db.query(func.count(RequestLog.id)).filter(
                RequestLog.site_id == site.id
            ).scalar()
            result.append({
                "id": site.id,
                "name": site.name,
                "is_active": site.is_active,
                "plan": site.plan,
                "message_limit": site.message_limit,
                "total_requests": total,
                "created_at": site.created_at.isoformat() if site.created_at else None,
            })
        return {"sites": result}
    finally:
        db.close()


@router.patch("/sites/{site_id}")
def update_site(site_id: int, req: UpdateSiteRequest, _=Depends(get_admin)):
    """Update plan and/or active status for a site. All fields are optional."""
    if req.plan is None and req.is_active is None:
        raise HTTPException(status_code=400, detail="Nothing to update — provide at least one field.")

    db = SessionLocal()
    try:
        site = db.query(Site).filter(Site.id == site_id).first()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")

        if req.plan is not None:
            try:
                config = get_plan_config(req.plan)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            site.plan = req.plan
            site.message_limit = config["limit"]
            site.period_start = datetime.datetime.now(timezone.utc) if config["resets_monthly"] else None

        if req.is_active is not None:
            site.is_active = req.is_active

        db.commit()
        return {
            "site_id": site.id,
            "name": site.name,
            "plan": site.plan,
            "is_active": site.is_active,
            "message_limit": site.message_limit,
        }
    finally:
        db.close()


class ResetUsageRequest(BaseModel):
    messages: bool = False
    files: bool = False


@router.post("/sites/{site_id}/reset")
def reset_site_usage(site_id: int, req: ResetUsageRequest, _=Depends(get_admin)):
    """
    Clear usage data for a site. Both fields default to false — opt in explicitly.
    - messages: deletes all request logs, resetting the message quota to zero.
    - files: deletes all ingested documents and chunks from the vector store.
    """
    if not req.messages and not req.files:
        raise HTTPException(status_code=400, detail="Nothing to reset — set messages and/or files to true.")

    db = SessionLocal()
    try:
        site = db.query(Site).filter(Site.id == site_id).first()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")

        cleared = []

        if req.messages:
            db.query(RequestLog).filter(RequestLog.site_id == site_id).delete()
            site.period_start = datetime.datetime.now(timezone.utc)
            db.commit()
            cleared.append("messages")

        if req.files:
            delete_site_chunks(site_id)
            cleared.append("files")

        return {"site_id": site_id, "cleared": cleared}
    finally:
        db.close()


@router.post("/sites/{site_id}/regenerate-key")
def regenerate_api_key(site_id: int, _=Depends(get_admin)):
    """
    Issue a new API key for a site. The previous key is immediately invalidated.
    The new key is returned once and cannot be retrieved again.
    """
    db = SessionLocal()
    try:
        site = db.query(Site).filter(Site.id == site_id).first()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        raw_key = secrets.token_urlsafe(32)
        site.api_key_prefix = raw_key[:8]
        site.api_key_hash = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
        db.commit()
        return {"site_id": site_id, "api_key": raw_key}
    finally:
        db.close()