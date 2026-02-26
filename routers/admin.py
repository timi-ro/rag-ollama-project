import hashlib
import os
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func

from middleware.auth import get_admin
from models.database import SessionLocal, Site, RequestLog

router = APIRouter(prefix="/admin")


class CreateSiteRequest(BaseModel):
    name: str
    plan: str = "free"
    message_limit: int = int(os.getenv("DEFAULT_MESSAGE_LIMIT", 100))


class UpdatePlanRequest(BaseModel):
    plan: str
    message_limit: int


@router.post("/sites")
def create_site(req: CreateSiteRequest, _=Depends(get_admin)):
    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    db = SessionLocal()
    try:
        site = Site(
            name=req.name,
            api_key_hash=key_hash,
            plan=req.plan,
            message_limit=req.message_limit,
        )
        db.add(site)
        db.commit()
        db.refresh(site)
        return {
            "site_id": site.id,
            "name": site.name,
            "api_key": raw_key,
            "plan": site.plan,
            "message_limit": site.message_limit,
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


@router.patch("/sites/{site_id}/deactivate")
def deactivate_site(site_id: int, _=Depends(get_admin)):
    db = SessionLocal()
    try:
        site = db.query(Site).filter(Site.id == site_id).first()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        site.is_active = False
        db.commit()
        return {"site_id": site_id, "is_active": False}
    finally:
        db.close()


@router.patch("/sites/{site_id}/plan")
def update_plan(site_id: int, req: UpdatePlanRequest, _=Depends(get_admin)):
    db = SessionLocal()
    try:
        site = db.query(Site).filter(Site.id == site_id).first()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        site.plan = req.plan
        site.message_limit = req.message_limit
        db.commit()
        return {"site_id": site_id, "plan": site.plan, "message_limit": site.message_limit}
    finally:
        db.close()
