from dataclasses import dataclass
from typing import Optional

MAX_CHUNK_CHARS = 1000
CHUNK_OVERLAP = 150


@dataclass
class Chunk:
    text: str
    file_type: str = "text"
    page: Optional[int] = None
    section_title: Optional[str] = None


def chunk_pdf(path: str) -> list:
    """Load PDF page-by-page and split within each page at paragraph boundaries."""
    from pypdf import PdfReader
    reader = PdfReader(path)
    chunks = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        for piece in _split_text(text):
            chunks.append(Chunk(text=piece, file_type="pdf", page=page_num))
    return chunks


def chunk_docx(path: str) -> list:
    """Parse DOCX headings to track section_title, split paragraph text."""
    from docx import Document
    doc = Document(path)
    chunks = []
    current_section = None
    buffer = []

    def _flush():
        if not buffer:
            return
        combined = "\n\n".join(buffer)
        for piece in _split_text(combined):
            chunks.append(Chunk(text=piece, file_type="docx", section_title=current_section))
        buffer.clear()

    for para in doc.paragraphs:
        style_name = para.style.name if para.style else ""
        text = para.text.strip()
        if not text:
            continue
        if style_name.startswith("Heading"):
            _flush()
            current_section = text
        else:
            buffer.append(text)

    _flush()
    return chunks


def chunk_text(text: str, file_type: str = "text") -> list:
    """Split plain text or markdown at paragraph boundaries."""
    return [Chunk(text=piece, file_type=file_type) for piece in _split_text(text)]


def _split_text(text: str) -> list:
    """Split at double-newline paragraph boundaries; subdivide oversized paragraphs."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=MAX_CHUNK_CHARS,
        chunk_overlap=CHUNK_OVERLAP,
    )
    result = []
    for para in paragraphs:
        if len(para) <= MAX_CHUNK_CHARS:
            result.append(para)
        else:
            result.extend(splitter.split_text(para))
    return result