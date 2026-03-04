import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from models.database import init_db
from routers import status, ingest, chat, admin, usage


def get_api_key(request: Request) -> str:
    return request.headers.get("X-API-Key", request.client.host)


limiter = Limiter(key_func=get_api_key, default_limits=["60/minute"])

app = FastAPI(
    title="RAG API",
    version="1.0.0",
    description=(
        "A multi-tenant Retrieval-Augmented Generation API built with LangChain and Ollama. "
        "Each site gets isolated document storage, API key authentication, and plan-based usage limits."
    ),
    openapi_tags=[
        {"name": "status",    "description": "Health check"},
        {"name": "chat",      "description": "Ask questions against your ingested documents"},
        {"name": "ingest",    "description": "Upload and manage documents. Enforces per-plan storage limits (free: 250 chunks, pro: 10 000 chunks, enterprise: unlimited)."},
        {"name": "usage",     "description": "Query message quota and storage usage. The response includes a 'storage' key with chunk_limit, chunks_used, and chunks_remaining."},
        {"name": "admin",     "description": "Admin-only site management"},
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
def startup():
    secret = os.getenv("ADMIN_SECRET", "")
    if secret in _INSECURE_SECRET_DEFAULTS:
        raise RuntimeError(
            "ADMIN_SECRET env var is not set or is still the default placeholder. "
            "Set a strong secret before starting the server."
        )
    init_db()


app.include_router(status.router)
app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(usage.router)
