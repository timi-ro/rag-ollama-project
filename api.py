from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from models.database import init_db
from routers import status, ingest, chat, admin


def get_api_key(request: Request) -> str:
    return request.headers.get("X-API-Key", request.client.host)


limiter = Limiter(key_func=get_api_key, default_limits=["60/minute"])

app = FastAPI(title="RAG API", version="1.0.0")

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse({"error": "RATE_LIMIT_EXCEEDED"}, status_code=429)


@app.on_event("startup")
def startup():
    init_db()


app.include_router(status.router)
app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(admin.router)
