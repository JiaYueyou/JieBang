from __future__ import annotations

import io

import pytest
from docx import Document

from app.core.exceptions import InvalidParameterError
from app.services.resume_parser import ResumeParser


SAMPLE_TEXT = "AI 工程师\nPython FastAPI Docker Redis"


def _docx_bytes(text: str) -> bytes:
    stream = io.BytesIO()
    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    document.save(stream)
    return stream.getvalue()


def test_parser_reads_docx_with_production_dependency():
    text, warnings = ResumeParser().parse(_docx_bytes(SAMPLE_TEXT), "resume.docx")

    assert text == SAMPLE_TEXT
    assert warnings == []


@pytest.mark.parametrize("suffix", ["png", "jpg", "jpeg"])
def test_parser_routes_supported_images_through_ocr(monkeypatch, suffix):
    monkeypatch.setattr(ResumeParser, "_ocr_image", lambda self, content: SAMPLE_TEXT)

    text, warnings = ResumeParser().parse(b"image-bytes", f"resume.{suffix}")

    assert text == SAMPLE_TEXT
    assert any("OCR" in warning for warning in warnings)


def test_parser_uses_ocr_for_scanned_pdf(monkeypatch):
    class Page:
        @staticmethod
        def extract_text():
            return ""

    class Reader:
        def __init__(self, _stream):
            self.pages = [Page()]

    monkeypatch.setattr("pypdf.PdfReader", Reader)
    monkeypatch.setattr(ResumeParser, "_ocr_pdf", lambda self, content: SAMPLE_TEXT)

    text, warnings = ResumeParser().parse(b"scanned-pdf", "resume.pdf")

    assert text == SAMPLE_TEXT
    assert any("OCR" in warning for warning in warnings)


def test_parser_rejects_legacy_doc_with_actionable_message():
    with pytest.raises(InvalidParameterError, match="PDF、DOCX、PNG、JPG 和 JPEG"):
        ResumeParser().parse(b"legacy", "resume.doc")


def test_ocr_normalizes_common_technical_token_confusions():
    assert ResumeParser._normalize_ocr_text(
        "FastAPl GraphQl PostgreSQl MySQl"
    ) == "FastAPI GraphQL PostgreSQL MySQL"


def test_optimized_ocr_selects_the_stronger_candidate(monkeypatch):
    from PIL import Image

    stream = io.BytesIO()
    Image.new("RGB", (400, 600), "white").save(stream, "PNG")
    calls = iter([
        ([[None, "Python", 0.70]], None),
        ([[None, "Python FastAPI Docker", 0.96]], None),
    ])
    monkeypatch.setattr(ResumeParser, "_rapid_ocr", classmethod(lambda cls: lambda image: next(calls)))

    text, diagnostics = ResumeParser().ocr_image_with_diagnostics(stream.getvalue())

    assert text == "Python FastAPI Docker"
    assert diagnostics["selected_variant"] == "enhanced"
    assert diagnostics["mean_confidence"] == 0.96
