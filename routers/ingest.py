import asyncio
import os
import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import Annotated
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from middleware.auth import get_site
from models.database import Site, SessionLocal
from services.concurrency import embed_semaphore, upload_semaphore
from services.embedding import embed_in_batches
from services.plans import get_plan_config
from services.vectorstore import upsert_chunks, delete_doc_chunks, list_docs, count_chunks, count_doc_chunks
from services import job_queue
from services.job_queue import UploadJob

router = APIRouter(prefix="/ingest", tags=["ingest"])

_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 10 * 1024 * 1024))  # default 10 MB
_STREAM_CHUNK = 64 * 1024  # 64 KB read buffer


def _safe_doc_id(filename: str) -> str:
    bare = Path(filename).name
    return re.sub(r"[^\w.\-]", "_", bare)[:255]


MAX_DOC_ID_CHARS = 255


def _check_chunk_limit(site: Site, doc_id: str, new_chunk_count: int):
    config = get_plan_config(site.plan)
    chunk_limit = config["chunk_limit"]
    if chunk_limit is None:
        return
    current_total = count_chunks(site.id)
    existing_doc = count_doc_chunks(site.id, doc_id)
    projected = (current_total - existing_doc) + new_chunk_count
    if projected > chunk_limit:
        raise HTTPException(
            status_code=413,
            detail={
                "error": "STORAGE_LIMIT_REACHED",
                "chunk_limit": chunk_limit,
                "chunks_used": current_total,
                "chunks_available": max(0, chunk_limit - current_total + existing_doc),
            },
        )


# ---------------------------------------------------------------------------
# Background worker function — called by job_queue.run_worker at startup
# ---------------------------------------------------------------------------

async def process_upload_job(job: UploadJob) -> dict:
    """Process a queued file upload: parse → split → embed → store."""
    # Re-fetch the site from DB so we have up-to-date plan/quota info
    with SessionLocal() as db:
        site = db.query(Site).filter(Site.id == job.site_id).first()
    if site is None:
        raise ValueError(f"Site {job.site_id} not found")

    loader = PyPDFLoader(job.tmp_path) if job.ext == ".pdf" else TextLoader(job.tmp_path)
    docs = loader.load()
    all_chunks = []
    for doc in docs:
        all_chunks.extend(_splitter.split_text(doc.page_content))

    if not all_chunks:
        raise ValueError("File produced no chunks")

    doc_id = _safe_doc_id(job.filename)

    try:
        _check_chunk_limit(site, doc_id, len(all_chunks))
    except HTTPException as exc:
        detail = exc.detail
        raise ValueError(detail if isinstance(detail, str) else str(detail))

    async with embed_semaphore:
        embeddings = await asyncio.get_event_loop().run_in_executor(
            None, embed_in_batches, all_chunks
        )
        upsert_chunks(site.id, doc_id, doc_id, all_chunks, embeddings)

    return {"ingested": len(all_chunks), "doc_id": doc_id}


# ---------------------------------------------------------------------------
# Helper: build the status payload for a job
# ---------------------------------------------------------------------------

def _job_response(job: UploadJob) -> dict:
    pos = job_queue.queue_position(job.job_id)
    eta = job_queue.eta_seconds(pos)
    return {
        "job_id": job.job_id,
        "status": job.status,
        "filename": job.filename,
        "queue_position": pos,
        "eta_seconds": eta,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "result": job.result,
        "error": job.error,
        "poll_url": f"/ingest/status/{job.job_id}",
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

class IngestTextRequest(BaseModel):
    content: Annotated[str, Field(min_length=1, max_length=MAX_UPLOAD_BYTES)]
    doc_id: Annotated[str, Field(min_length=1, max_length=MAX_DOC_ID_CHARS, pattern=r"^[\w.\-]+$")]
    title: Annotated[str, Field(max_length=500)] = ""


@router.post("/text")
async def ingest_text(req: IngestTextRequest, site: Site = Depends(get_site)):
    async with upload_semaphore:
        chunks = _splitter.split_text(req.content)
        if not chunks:
            raise HTTPException(status_code=400, detail="Content produced no chunks")
        _check_chunk_limit(site, req.doc_id, len(chunks))
        async with embed_semaphore:
            embeddings = await asyncio.get_event_loop().run_in_executor(
                None, embed_in_batches, chunks
            )
            upsert_chunks(site.id, req.doc_id, req.title, chunks, embeddings)
    return {"ingested": len(chunks), "doc_id": req.doc_id}


@router.post("/file", status_code=202)
async def ingest_file(file: UploadFile = File(...), site: Site = Depends(get_site)):
    """
    Accepts a file upload and queues it for processing.
    Returns immediately with a job_id. Poll /ingest/status/{job_id} for progress.
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
        )

    # Stream directly to a temp file — never buffer the whole file in RAM
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp_path = tmp.name
        bytes_written = 0
        while True:
            chunk = await file.read(_STREAM_CHUNK)
            if not chunk:
                break
            bytes_written += len(chunk)
            if bytes_written > MAX_UPLOAD_BYTES:
                tmp.close()
                os.unlink(tmp_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
                )
            tmp.write(chunk)

    job = job_queue.create_job(site.id, site.plan, tmp_path, ext, file.filename)
    return _job_response(job)


@router.get("/status/{job_id}")
def get_upload_status(job_id: str, site: Site = Depends(get_site)):
    """Poll the status of a queued file upload."""
    job = job_queue.get_job(job_id, site.id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_response(job)


@router.post("/retry/{job_id}", status_code=202)
def retry_upload(job_id: str, site: Site = Depends(get_site)):
    """Re-queue a failed upload job. The original file is reused — no need to re-upload."""
    job = job_queue.requeue_job(job_id, site.id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found or not in failed state",
        )
    return _job_response(job)


@router.get("/documents")
def list_documents(site: Site = Depends(get_site)):
    return {"documents": list_docs(site.id)}


@router.delete("/{doc_id}")
def delete_document(doc_id: str, site: Site = Depends(get_site)):
    delete_doc_chunks(site.id, doc_id)
    return {"deleted": doc_id}