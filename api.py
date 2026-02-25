import uuid
import datetime
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Header, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from main import initialize, query, query_stream

app = FastAPI(title="RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".html", ".htm", ".csv"}

# Load config.json
CONFIG_PATH = Path("config.json")

def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise RuntimeError(
            "config.json not found. Copy config.example.json to config.json and add your tenants."
        )
    with open(CONFIG_PATH) as f:
        return json.load(f)

try:
    _config = _load_config()
    # Reverse lookup: api_key -> (tenant_id, tenant_config)
    _key_to_tenant: dict[str, tuple[str, dict]] = {
        v["api_key"]: (k, v) for k, v in _config["tenants"].items()
    }
except RuntimeError as e:
    print(f"WARNING: {e}")
    _config = {"tenants": {}}
    _key_to_tenant = {}

# In-memory caches
_chains: dict = {}   # "{tenant_id}:{model}" -> chain
_sessions: dict = {} # session_id -> {chat_history, model, tenant, created_at}


# --- Auth dependency ---

def get_tenant(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key not in _key_to_tenant:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return _key_to_tenant[x_api_key]  # returns (tenant_id, tenant_config)


# --- Helpers ---

def _get_chain(tenant_id: str, model: str):
    cache_key = f"{tenant_id}:{model}"
    if cache_key not in _chains:
        docs_dir = f"./docs/{tenant_id}"
        persist_dir = f"./chroma_db/{tenant_id}/{model}"
        try:
            _chains[cache_key] = initialize(model, docs_dir=docs_dir, persist_dir=persist_dir)
        except Exception as e:
            _handle_error(e, model)
    return _chains[cache_key]


def _invalidate_chain(tenant_id: str, model: str):
    _chains.pop(f"{tenant_id}:{model}", None)


def _to_langchain_history(history: list[dict]) -> list:
    result = []
    for msg in history:
        if msg["role"] == "user":
            result.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            result.append(AIMessage(content=msg["content"]))
    return result


def _get_session(session_id: str, tenant_id: str) -> dict:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions[session_id]
    if session["tenant"] != tenant_id:
        raise HTTPException(status_code=403, detail="Session does not belong to this tenant")
    return session


def _handle_error(e: Exception, model: str):
    if "not found" in str(e).lower() or "404" in str(e):
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model}' not found. Run: ollama pull {model}",
        )
    raise HTTPException(status_code=500, detail=str(e))


# --- Pydantic models ---

class ChatRequest(BaseModel):
    question: str
    model: str = "llama3.2"
    chat_history: list[dict] = []

class ChatResponse(BaseModel):
    answer: str
    sources: list[str]

class SessionCreateRequest(BaseModel):
    model: str = "llama3.2"

class SessionResponse(BaseModel):
    session_id: str
    model: str
    created_at: str

class SessionChatRequest(BaseModel):
    question: str


# --- Health ---

@app.get("/health")
def health():
    return {"status": "ok"}


# --- Stateless chat (client owns history) ---

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, tenant=Depends(get_tenant)):
    tenant_id, _ = tenant
    chain = _get_chain(tenant_id, req.model)
    history = _to_langchain_history(req.chat_history)
    try:
        answer, sources = query(req.question, chain, history)
    except Exception as e:
        _handle_error(e, req.model)
    return ChatResponse(answer=answer, sources=sources)


@app.post("/chat/stream")
def chat_stream(req: ChatRequest, tenant=Depends(get_tenant)):
    tenant_id, _ = tenant
    chain = _get_chain(tenant_id, req.model)
    history = _to_langchain_history(req.chat_history)

    def generate():
        try:
            for token, sources in query_stream(req.question, chain, history):
                if sources is not None:
                    yield f"data: [SOURCES] {','.join(sources)}\n\n"
                else:
                    yield f"data: {token}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# --- Sessions (server owns history) ---

@app.post("/sessions", response_model=SessionResponse)
def create_session(req: SessionCreateRequest, tenant=Depends(get_tenant)):
    tenant_id, _ = tenant
    _get_chain(tenant_id, req.model)  # validate model exists
    session_id = str(uuid.uuid4())
    created_at = datetime.datetime.utcnow().isoformat()
    _sessions[session_id] = {
        "chat_history": [],
        "model": req.model,
        "tenant": tenant_id,
        "created_at": created_at,
    }
    return SessionResponse(session_id=session_id, model=req.model, created_at=created_at)


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str, tenant=Depends(get_tenant)):
    tenant_id, _ = tenant
    _get_session(session_id, tenant_id)
    del _sessions[session_id]
    return {"deleted": session_id}


@app.post("/sessions/{session_id}/chat", response_model=ChatResponse)
def session_chat(session_id: str, req: SessionChatRequest, tenant=Depends(get_tenant)):
    tenant_id, _ = tenant
    session = _get_session(session_id, tenant_id)
    chain = _get_chain(tenant_id, session["model"])
    try:
        answer, sources = query(req.question, chain, session["chat_history"])
    except Exception as e:
        _handle_error(e, session["model"])
    return ChatResponse(answer=answer, sources=sources)


@app.post("/sessions/{session_id}/chat/stream")
def session_chat_stream(session_id: str, req: SessionChatRequest, tenant=Depends(get_tenant)):
    tenant_id, _ = tenant
    session = _get_session(session_id, tenant_id)
    chain = _get_chain(tenant_id, session["model"])

    def generate():
        try:
            for token, sources in query_stream(req.question, chain, session["chat_history"]):
                if sources is not None:
                    yield f"data: [SOURCES] {','.join(sources)}\n\n"
                else:
                    yield f"data: {token}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# --- Documents ---

@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...), tenant=Depends(get_tenant)):
    tenant_id, tenant_config = tenant
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
        )
    docs_dir = Path(f"./docs/{tenant_id}")
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / file.filename).write_bytes(await file.read())
    _invalidate_chain(tenant_id, tenant_config["model"])
    return {"uploaded": file.filename, "tenant": tenant_id}


@app.get("/documents")
def list_documents(tenant=Depends(get_tenant)):
    tenant_id, _ = tenant
    docs_dir = Path(f"./docs/{tenant_id}")
    if not docs_dir.exists():
        return {"documents": []}
    files = [
        f.name for f in docs_dir.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return {"documents": files}


@app.delete("/documents/{filename}")
def delete_document(filename: str, tenant=Depends(get_tenant)):
    tenant_id, tenant_config = tenant
    file_path = Path(f"./docs/{tenant_id}/{filename}")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"'{filename}' not found")
    file_path.unlink()
    _invalidate_chain(tenant_id, tenant_config["model"])
    return {"deleted": filename, "tenant": tenant_id}