import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from middleware.auth import get_site
from models.database import Site
from services.embedding import get_embeddings
from services.vectorstore import upsert_chunks, delete_doc_chunks, list_docs

router = APIRouter(prefix="/ingest")

_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


class IngestTextRequest(BaseModel):
    content: str
    doc_id: str
    title: str = ""


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
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(await file.read())
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
        upsert_chunks(site.id, file.filename, file.filename, all_chunks, embeddings)
    finally:
        os.unlink(tmp_path)
    return {"ingested": len(all_chunks), "doc_id": file.filename}


@router.get("/documents")
def list_documents(site: Site = Depends(get_site)):
    return {"documents": list_docs(site.id)}


@router.delete("/{doc_id}")
def delete_document(doc_id: str, site: Site = Depends(get_site)):
    delete_doc_chunks(site.id, doc_id)
    return {"deleted": doc_id}
