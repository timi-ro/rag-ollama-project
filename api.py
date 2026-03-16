import asyncio
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from models.database import init_db
from routers import status, ingest, chat, admin, usage
from routers.ingest import process_upload_job
from routers.chat import process_chat_job
from services import job_queue, chat_queue


def get_api_key(request: Request) -> str:
    return request.headers.get("X-API-Key", request.client.host)


limiter = Limiter(key_func=get_api_key, default_limits=["60/minute"])

app = FastAPI(
    title="RAG API",
    version="1.0.0",
    description=(
        "A multi-tenant Retrieval-Augmented Generation API built with LangChain and Ollama. "
        "Each site gets isolated document storage, API key authentication, and plan-based usage limits. "
        "Chat supports three modes: sync (default), streaming SSE (?stream=true), and async (?async=true). "
        "File ingestion is always async (202 + poll)."
    ),
    openapi_tags=[
        {"name": "status",    "description": "Health check. Returns server version and active Ollama model."},
        {"name": "chat",      "description": (
            "Ask questions against your ingested documents. "
            "Add ?stream=true for SSE token streaming (first token in ~1 s on fast hardware). "
            "Add ?async=true to queue the request and get a job_id; poll GET /chat/status/{job_id} for the result."
        )},
        {"name": "ingest",    "description": (
            "Upload and manage documents. Enforces per-plan storage limits "
            "(free: 250 chunks, pro: 10 000 chunks, enterprise: unlimited). "
            "File uploads (POST /ingest/file) return 202 immediately with a job_id. "
            "Poll GET /ingest/status/{job_id} for progress, queue position, and ETA. "
            "Failed jobs can be retried via POST /ingest/retry/{job_id} without re-uploading the file. "
            "Text ingestion (POST /ingest/text) is synchronous."
        )},
        {"name": "usage",     "description": "Query message quota and storage usage. The response includes a 'storage' key with chunk_limit, chunks_used, and chunks_remaining."},
        {"name": "admin",     "description": (
            "Admin-only site management. Valid plans: free, pro, enterprise. "
            "PATCH /admin/sites/{id} updates plan and/or is_active in one call. "
            "POST /admin/sites/{id}/reset clears message logs (messages: true) and/or all vector chunks (files: true) — both fields default to false. "
            "POST /admin/sites/{id}/regenerate-key issues a new API key; the previous key is immediately invalidated and the new one is shown once."
        )},
    ],
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["X-API-Key", "X-Admin-Secret", "Content-Type"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse({"error": "RATE_LIMIT_EXCEEDED"}, status_code=429)


_INSECURE_SECRET_DEFAULTS = {"", "change-me-in-production"}


@app.on_event("startup")
async def startup():
    secret = os.getenv("ADMIN_SECRET", "")
    if secret in _INSECURE_SECRET_DEFAULTS:
        raise RuntimeError(
            "ADMIN_SECRET env var is not set or is still the default placeholder. "
            "Set a strong secret before starting the server."
        )
    init_db()
    asyncio.create_task(job_queue.run_worker(process_upload_job))
    asyncio.create_task(chat_queue.run_worker(process_chat_job))


app.include_router(status.router)
app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(usage.router)
