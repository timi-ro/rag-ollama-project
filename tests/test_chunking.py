import os
import tempfile

import pytest

from services.chunking import Chunk, MAX_CHUNK_CHARS, _split_text, chunk_text, chunk_docx, chunk_pdf


# ---------------------------------------------------------------------------
# _split_text — paragraph-boundary splitting
# ---------------------------------------------------------------------------

class TestSplitText:
    def test_empty_string_returns_empty(self):
        assert _split_text("") == []

    def test_whitespace_only_returns_empty(self):
        assert _split_text("   \n\n   ") == []

    def test_single_short_paragraph(self):
        assert _split_text("Hello world.") == ["Hello world."]

    def test_multiple_paragraphs(self):
        result = _split_text("First.\n\nSecond.\n\nThird.")
        assert result == ["First.", "Second.", "Third."]

    def test_paragraph_at_exact_limit_is_kept_whole(self):
        para = "x" * MAX_CHUNK_CHARS
        result = _split_text(para)
        assert result == [para]

    def test_paragraph_over_limit_is_subdivided(self):
        long_para = "word " * 300  # ~1500 chars
        result = _split_text(long_para)
        assert len(result) > 1
        for piece in result:
            assert len(piece) <= MAX_CHUNK_CHARS + 200  # allow splitter overlap

    def test_blank_paragraphs_between_content_are_ignored(self):
        result = _split_text("A.\n\n\n\n\n\nB.")
        assert result == ["A.", "B."]

    def test_leading_trailing_whitespace_stripped(self):
        result = _split_text("  hello world  ")
        assert result == ["hello world"]


# ---------------------------------------------------------------------------
# chunk_text — plain text / markdown
# ---------------------------------------------------------------------------

class TestChunkText:
    def test_returns_chunk_objects(self):
        result = chunk_text("Some content.")
        assert all(isinstance(c, Chunk) for c in result)

    def test_empty_input_returns_empty(self):
        assert chunk_text("") == []

    def test_default_file_type_is_text(self):
        assert chunk_text("content")[0].file_type == "text"

    def test_custom_file_type_passed_through(self):
        assert chunk_text("content", file_type="md")[0].file_type == "md"

    def test_page_is_always_none(self):
        assert chunk_text("content")[0].page is None

    def test_section_title_is_always_none(self):
        assert chunk_text("content")[0].section_title is None

    def test_text_content_preserved(self):
        assert chunk_text("Hello world.")[0].text == "Hello world."

    def test_multiple_paragraphs_produce_multiple_chunks(self):
        result = chunk_text("Para one.\n\nPara two.\n\nPara three.")
        assert len(result) == 3

    def test_long_content_splits_into_multiple_chunks(self):
        long_text = "word " * 400
        result = chunk_text(long_text)
        assert len(result) > 1


# ---------------------------------------------------------------------------
# chunk_docx — heading-aware DOCX parsing
# ---------------------------------------------------------------------------

def _make_docx(paragraphs: list) -> str:
    """Write a temporary DOCX with (style_name, text) pairs. Returns the file path."""
    from docx import Document
    doc = Document()
    for style_name, text in paragraphs:
        p = doc.add_paragraph(text)
        if style_name:
            p.style = doc.styles[style_name]
    tmp = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
    doc.save(tmp.name)
    tmp.close()
    return tmp.name


class TestChunkDocx:
    def test_empty_document_returns_empty(self):
        path = _make_docx([])
        try:
            assert chunk_docx(path) == []
        finally:
            os.unlink(path)

    def test_plain_paragraphs_no_heading_have_no_section(self):
        path = _make_docx([("Normal", "First"), ("Normal", "Second")])
        try:
            result = chunk_docx(path)
            assert len(result) >= 1
            assert all(c.section_title is None for c in result)
        finally:
            os.unlink(path)

    def test_all_chunks_have_docx_file_type(self):
        path = _make_docx([("Normal", "content")])
        try:
            assert all(c.file_type == "docx" for c in chunk_docx(path))
        finally:
            os.unlink(path)

    def test_heading_sets_section_title_on_following_paragraphs(self):
        path = _make_docx([
            ("Heading 1", "Introduction"),
            ("Normal", "Intro content here."),
        ])
        try:
            result = chunk_docx(path)
            assert any(c.section_title == "Introduction" for c in result)
        finally:
            os.unlink(path)

    def test_multiple_headings_tag_their_own_sections(self):
        path = _make_docx([
            ("Heading 1", "Chapter One"),
            ("Normal", "Chapter one body."),
            ("Heading 1", "Chapter Two"),
            ("Normal", "Chapter two body."),
        ])
        try:
            result = chunk_docx(path)
            titles = {c.section_title for c in result}
            assert "Chapter One" in titles
            assert "Chapter Two" in titles
        finally:
            os.unlink(path)

    def test_heading_2_also_sets_section_title(self):
        path = _make_docx([
            ("Heading 2", "Subsection"),
            ("Normal", "Subsection body."),
        ])
        try:
            result = chunk_docx(path)
            assert any(c.section_title == "Subsection" for c in result)
        finally:
            os.unlink(path)

    def test_page_is_always_none(self):
        path = _make_docx([("Normal", "content")])
        try:
            assert all(c.page is None for c in chunk_docx(path))
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# chunk_pdf — page-aware PDF parsing (mocked PdfReader)
# ---------------------------------------------------------------------------

class TestChunkPdf:
    def test_single_page_produces_one_chunk(self, mocker):
        mock_page = mocker.MagicMock()
        mock_page.extract_text.return_value = "Page content here."
        mocker.patch("pypdf.PdfReader", return_value=mocker.MagicMock(pages=[mock_page]))

        result = chunk_pdf("/fake/doc.pdf")
        assert len(result) == 1
        assert result[0].file_type == "pdf"
        assert result[0].page == 1
        assert result[0].text == "Page content here."

    def test_page_numbers_increment(self, mocker):
        pages = [mocker.MagicMock(), mocker.MagicMock()]
        pages[0].extract_text.return_value = "Page one."
        pages[1].extract_text.return_value = "Page two."
        mocker.patch("pypdf.PdfReader", return_value=mocker.MagicMock(pages=pages))

        result = chunk_pdf("/fake/doc.pdf")
        assert result[0].page == 1
        assert result[1].page == 2

    def test_empty_pages_are_skipped(self, mocker):
        pages = [mocker.MagicMock(), mocker.MagicMock()]
        pages[0].extract_text.return_value = ""
        pages[1].extract_text.return_value = "Only non-empty page."
        mocker.patch("pypdf.PdfReader", return_value=mocker.MagicMock(pages=pages))

        result = chunk_pdf("/fake/doc.pdf")
        assert len(result) == 1
        assert result[0].page == 2

    def test_whitespace_only_pages_are_skipped(self, mocker):
        page = mocker.MagicMock()
        page.extract_text.return_value = "   \n   "
        mocker.patch("pypdf.PdfReader", return_value=mocker.MagicMock(pages=[page]))

        assert chunk_pdf("/fake/doc.pdf") == []

    def test_multipage_long_content_splits_within_page(self, mocker):
        page = mocker.MagicMock()
        page.extract_text.return_value = ("word " * 300)  # ~1500 chars
        mocker.patch("pypdf.PdfReader", return_value=mocker.MagicMock(pages=[page]))

        result = chunk_pdf("/fake/doc.pdf")
        assert len(result) > 1
        assert all(c.page == 1 for c in result)