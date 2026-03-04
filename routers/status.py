import os
from fastapi import APIRouter

router = APIRouter(tags=["status"])


@router.get("/status")
def status():
    return {
        "status": "ok",
        "version": "1.0.0",
        "model": os.getenv("OLLAMA_MODEL", "llama3.2"),
    }
