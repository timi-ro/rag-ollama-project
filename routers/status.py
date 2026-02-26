from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
def status():
    return {"status": "ok", "version": "1.0.0"}
