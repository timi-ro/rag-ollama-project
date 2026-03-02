import hmac
import os
import bcrypt
from fastapi import Header, HTTPException
from models.database import SessionLocal, Site
from dotenv import load_dotenv

load_dotenv()


def get_site(x_api_key: str = Header(..., alias="X-API-Key")) -> Site:
    """Validate X-API-Key and return the matching Site."""
    prefix = x_api_key[:8]
    db = SessionLocal()
    try:
        site = db.query(Site).filter(
            Site.api_key_prefix == prefix,
            Site.is_active == True,
        ).first()
    finally:
        db.close()
    if not site or not bcrypt.checkpw(x_api_key.encode(), site.api_key_hash.encode()):
        raise HTTPException(status_code=401, detail={"error": "INVALID_API_KEY"})
    return site


def get_admin(x_admin_secret: str = Header(..., alias="X-Admin-Secret")) -> bool:
    """Validate X-Admin-Secret for admin endpoints."""
    admin_secret = os.getenv("ADMIN_SECRET", "change-me-in-production")
    if not hmac.compare_digest(x_admin_secret, admin_secret):
        raise HTTPException(status_code=401, detail={"error": "INVALID_ADMIN_SECRET"})
    return True
