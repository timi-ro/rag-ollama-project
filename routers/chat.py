from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func

from middleware.auth import get_site
from models.database import SessionLocal, Site, RequestLog
from services.embedding import get_embeddings
from services.vectorstore import query_chunks
from services.llm import get_llm, generate_answer

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    conversation_history: list[dict] = []


@router.post("/chat")
def chat(req: ChatRequest, site: Site = Depends(get_site)):
    db = SessionLocal()
    try:
        # Check message limit
        used = db.query(func.count(RequestLog.id)).filter(
            RequestLog.site_id == site.id,
            RequestLog.endpoint == "/chat",
            RequestLog.status_code == 200,
        ).scalar()
        if used >= site.message_limit:
            raise HTTPException(status_code=429, detail={"error": "PLAN_LIMIT_REACHED"})

        # Embed question and retrieve relevant chunks
        question_embedding = get_embeddings().embed_query(req.question)
        results = query_chunks(site.id, question_embedding, n_results=5)

        context = "\n\n".join(results["documents"][0]) if results.get("documents") else ""
        sources = list({
            meta["doc_id"] for meta in results["metadatas"][0]
        }) if results.get("metadatas") else []

        # Generate answer
        answer = generate_answer(get_llm(), req.question, context, req.conversation_history)

        # Log successful request
        db.add(RequestLog(site_id=site.id, endpoint="/chat", status_code=200))
        db.commit()

        return {"answer": answer, "sources": sources}
    except HTTPException:
        raise
    except Exception as e:
        db.add(RequestLog(site_id=site.id, endpoint="/chat", status_code=500))
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
