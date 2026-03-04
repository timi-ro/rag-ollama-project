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
from models.database import Site
from services.embedding import get_embeddings
from services.vectorstore import upsert_chunks, delete_doc_chunks, list_docs

router = APIRouter(prefix="/ingest", tags=["ingest"])

_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 10 * 1024 * 1024))  # default 10 MB


def _safe_doc_id(filename: str) -> str:
    """Return a sanitized doc_id from an upload filename.

    Strips directory components and replaces any character that is not
    alphanumeric, a dash, underscore, or dot with an underscore.
    """
    bare = Path(filename).name  # drop any path traversal components
    return re.sub(r"[^\w.\-]", "_", bare)[:255]


MAX_DOC_ID_CHARS = 255


class IngestTextRequest(BaseModel):
    content: Annotated[str, Field(min_length=1, max_length=MAX_UPLOAD_BYTES)]
    doc_id: Annotated[str, Field(min_length=1, max_length=MAX_DOC_ID_CHARS, pattern=r"^[\w.\-]+$")]
    title: Annotated[str, Field(max_length=500)] = ""


@router.post("/text")
def ingest_text(req: IngestTextRequest, site: Site = Depends(get_site)):
    chunks = _splitter.split_text(req.content)
    if not chunks:
        raise HTTPException(status_code=400, detail="Content produced no chunks")
    embeddings = get_embeddings().embed_documents(chunks)
    upsert_chunks(site.id, req.doc_id, req.title, chunks, embeddings)
    return {"ingested": len(chunks), "doc_id": req.doc_id}


@router.post("/file")
async def ingest_file(file: UploadFile = File(...), site: Site = Depends(get_site)):
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
        )
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    try:
        loader = PyPDFLoader(tmp_path) if ext == ".pdf" else TextLoader(tmp_path)
        docs = loader.load()
        all_chunks = []
        for doc in docs:
            all_chunks.extend(_splitter.split_text(doc.page_content))
        if not all_chunks:
            raise HTTPException(status_code=400, detail="File produced no chunks")
        embeddings = get_embeddings().embed_documents(all_chunks)
        doc_id = _safe_doc_id(file.filename)
        upsert_chunks(site.id, doc_id, doc_id, all_chunks, embeddings)
    finally:
        os.unlink(tmp_path)
    return {"ingested": len(all_chunks), "doc_id": doc_id}


@router.get("/documents")
def list_documents(site: Site = Depends(get_site)):
    return {"documents": list_docs(site.id)}


@router.delete("/{doc_id}")
def delete_document(doc_id: str, site: Site = Depends(get_site)):
    delete_doc_chunks(site.id, doc_id)
    return {"deleted": doc_id}
