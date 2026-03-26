import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Annotated, Literal, Optional

from middleware.auth import get_site
from models.database import SessionLocal, Site, RequestLog
from services.cache import get_cached, set_cached
from services.concurrency import embed_semaphore, llm_semaphore
from services.embedding import get_embeddings
from services.plans import get_plan_config, get_usage_count
from services.vectorstore import query_chunks
from services.llm import get_llm, generate_answer, generate_answer_stream
from services import chat_queue
from services.chat_queue import ChatJob

router = APIRouter(tags=["chat"])

MAX_QUESTION_CHARS = 4096
MAX_HISTORY_TURNS = 20
MAX_HISTORY_MSG_CHARS = 4096


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: Annotated[str, Field(max_length=MAX_HISTORY_MSG_CHARS)]


class ChatRequest(BaseModel):
    question: Annotated[str, Field(min_length=1, max_length=MAX_QUESTION_CHARS)]
    conversation_history: Annotated[list[HistoryMessage], Field(max_length=MAX_HISTORY_TURNS)] = []


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

async def _embed_question(question: str) -> list:
    async with embed_semaphore:
        return await asyncio.get_running_loop().run_in_executor(
            None, get_embeddings().embed_query, question
        )


async def _generate_sync(llm, question: str, context: str, history: list) -> str:
    async with llm_semaphore:
        return await asyncio.get_running_loop().run_in_executor(
            None, generate_answer, llm, question, context, history
        )


def _extract_results(results: dict) -> tuple:
    context = "\n\n".join(results["documents"][0]) if results.get("documents") else ""
    sources = list({
        meta["doc_id"] for meta in results["metadatas"][0]
    }) if results.get("metadatas") else []
    return context, sources


# ---------------------------------------------------------------------------
# Background worker for async chat mode
# ---------------------------------------------------------------------------

async def process_chat_job(job: ChatJob) -> dict:
    """Process a queued chat job: quota check → embed → retrieve → generate → cache → log."""
    db = SessionLocal()
    try:
        site = db.query(Site).filter(Site.id == job.site_id).first()
        if site is None:
            raise ValueError(f"Site {job.site_id} not found")

        config = get_plan_config(site.plan)
        if not config["unlimited"]:
            used, was_reset = get_usage_count(site, db)
            if was_reset:
                db.commit()
            if used >= site.message_limit:
                raise ValueError("PLAN_LIMIT_REACHED")

        cached = get_cached(job.site_id, job.question)
        if cached:
            db.add(RequestLog(site_id=site.id, endpoint="/chat", status_code=200))
            db.commit()
            return {**cached, "from_cache": True}

        question_embedding = await _embed_question(job.question)
        results = query_chunks(site.id, question_embedding, n_results=5)
        context, sources = _extract_results(results)

        answer = await _generate_sync(get_llm(site), job.question, context, job.conversation_history)
        set_cached(job.site_id, job.question, answer, sources)

        db.add(RequestLog(site_id=site.id, endpoint="/chat", status_code=200))
        db.commit()
        return {"answer": answer, "sources": sources}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Streaming SSE generator
# ---------------------------------------------------------------------------

async def _stream_chat(site_id: int, req: ChatRequest, doc_id: Optional[str] = None, file_type: Optional[str] = None):
    cached = get_cached(site_id, req.question)
    if cached:
        yield f"data: {json.dumps({**cached, 'done': True, 'from_cache': True})}\n\n"
        return

    db = SessionLocal()
    try:
        site = db.query(Site).filter(Site.id == site_id).first()
        if site is None:
            yield f"data: {json.dumps({'error': 'Site not found', 'done': True})}\n\n"
            return

        config = get_plan_config(site.plan)
        if not config["unlimited"]:
            used, was_reset = get_usage_count(site, db)
            if was_reset:
                db.commit()
            if used >= site.message_limit:
                yield f"data: {json.dumps({'error': 'PLAN_LIMIT_REACHED', 'done': True})}\n\n"
                return

        question_embedding = await _embed_question(req.question)
        results = query_chunks(site.id, question_embedding, n_results=5, doc_id=doc_id, file_type=file_type)
        context, sources = _extract_results(results)

        llm = get_llm(site)
        full_answer = ""
        async with llm_semaphore:
            async for token in generate_answer_stream(llm, req.question, context, req.conversation_history):
                full_answer += token
                yield f"data: {json.dumps({'token': token})}\n\n"

        yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"
        set_cached(site_id, req.question, full_answer, sources)
        db.add(RequestLog(site_id=site.id, endpoint="/chat", status_code=200))
        db.commit()
    except Exception as exc:
        yield f"data: {json.dumps({'error': str(exc), 'done': True})}\n\n"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/chat")
async def chat(
    req: ChatRequest,
    stream: bool = Query(False),
    async_mode: bool = Query(False, alias="async"),
    doc_id: Optional[str] = Query(None, description="Limit retrieval to a specific document"),
    file_type: Optional[str] = Query(None, description="Limit retrieval to a specific file type (pdf, docx, text, md)"),
    site: Site = Depends(get_site),
):
    # Async mode: queue the job and return 202 immediately
    if async_mode:
        history = [m.model_dump() for m in req.conversation_history]
        job = chat_queue.create_job(site.id, req.question, history)
        return JSONResponse(
            {"job_id": job.job_id, "status": "queued", "poll_url": f"/chat/status/{job.job_id}"},
            status_code=202,
        )

    # Streaming mode: SSE token stream
    if stream:
        return StreamingResponse(_stream_chat(site.id, req, doc_id=doc_id, file_type=file_type), media_type="text/event-stream")

    # Sync mode: cache → semaphores → response
    cached = get_cached(site.id, req.question)
    if cached:
        return {**cached, "from_cache": True}

    db = SessionLocal()
    try:
        site = db.query(Site).filter(Site.id == site.id).first()

        config = get_plan_config(site.plan)
        if not config["unlimited"]:
            used, was_reset = get_usage_count(site, db)
            if was_reset:
                db.commit()
            if used >= site.message_limit:
                raise HTTPException(status_code=429, detail={
                    "error": "PLAN_LIMIT_REACHED",
                    "plan": site.plan,
                    "used": used,
                    "limit": site.message_limit,
                })

        question_embedding = await _embed_question(req.question)
        results = query_chunks(site.id, question_embedding, n_results=5, doc_id=doc_id, file_type=file_type)
        context, sources = _extract_results(results)

        answer = await _generate_sync(get_llm(site), req.question, context, req.conversation_history)
        set_cached(site.id, req.question, answer, sources)

        db.add(RequestLog(site_id=site.id, endpoint="/chat", status_code=200))
        db.commit()
        return {"answer": answer, "sources": sources}
    except HTTPException:
        raise
    except Exception:
        db.add(RequestLog(site_id=site.id, endpoint="/chat", status_code=500))
        db.commit()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@router.get("/chat/status/{job_id}")
def get_chat_status(job_id: str, site: Site = Depends(get_site)):
    """Poll the status of an async chat job."""
    job = chat_queue.get_job(job_id, site.id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.job_id,
        "status": job.status,
        "result": job.result,
        "error": job.error,
        "poll_url": f"/chat/status/{job.job_id}",
    }