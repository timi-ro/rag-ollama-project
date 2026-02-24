from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage
from main import initialize, query, query_stream

app = FastAPI(title="RAG API")

# Cache initialized chains per model
_chains: dict = {}


def get_chain(model: str):
    if model not in _chains:
        try:
            _chains[model] = initialize(model)
        except Exception as e:
            if "not found" in str(e).lower() or "404" in str(e):
                raise HTTPException(
                    status_code=404,
                    detail=f"Model '{model}' not found. Run: ollama pull {model}",
                )
            raise HTTPException(status_code=500, detail=str(e))
    return _chains[model]


def to_langchain_history(history: list[dict]) -> list:
    messages = []
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    return messages


class ChatRequest(BaseModel):
    question: str
    model: str = "llama3.2"
    chat_history: list[dict] = []


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    chain = get_chain(req.model)
    history = to_langchain_history(req.chat_history)
    try:
        answer, sources = query(req.question, chain, history)
    except Exception as e:
        if "not found" in str(e).lower() or "404" in str(e):
            raise HTTPException(
                status_code=404,
                detail=f"Model '{req.model}' not found. Run: ollama pull {req.model}",
            )
        raise HTTPException(status_code=500, detail=str(e))
    return ChatResponse(answer=answer, sources=sources)


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    chain = get_chain(req.model)
    history = to_langchain_history(req.chat_history)

    def generate():
        try:
            for token, sources in query_stream(req.question, chain, history):
                if sources is not None:
                    yield f"data: [SOURCES] {','.join(sources)}\n\n"
                else:
                    yield f"data: {token}\n\n"
        except Exception as e:
            if "not found" in str(e).lower() or "404" in str(e):
                yield f"data: [ERROR] Model '{req.model}' not found. Run: ollama pull {req.model}\n\n"
            else:
                yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")