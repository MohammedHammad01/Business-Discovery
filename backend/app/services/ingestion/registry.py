"""Adapter registry: picks the right deterministic extractor for an upload."""

from __future__ import annotations

from app.services.ingestion.base import IngestionError, NormalizedSource, SourceAdapter
from app.services.ingestion.docx_adapter import DocxAdapter, docx_available
from app.services.ingestion.image_adapter import ImageAdapter, ocr_available
from app.services.ingestion.pdf_adapter import PdfAdapter, pdf_available
from app.services.ingestion.text_adapter import TextAdapter
from app.services.ingestion.url_adapter import UrlAdapter

# Order matters: the most specific adapters are tried first, TextAdapter last
# because it also claims any `text/*` content type.
ADAPTERS: list[SourceAdapter] = [PdfAdapter(), DocxAdapter(), ImageAdapter(), TextAdapter()]

SUPPORTED_EXTENSIONS = "txt, md, log, csv, vtt, srt, pdf, docx, png, jpg, jpeg, webp, gif, bmp"


def select_adapter(filename: str, content_type: str) -> SourceAdapter:
    for adapter in ADAPTERS:
        if adapter.supports(filename, content_type or ""):
            return adapter
    raise IngestionError(
        f"'{filename}' is not a supported file type. Supported: {SUPPORTED_EXTENSIONS}."
    )


def extract_file(filename: str, content_type: str, data: bytes) -> NormalizedSource:
    if not data:
        raise IngestionError(f"'{filename}' is empty.")
    return select_adapter(filename, content_type).extract(filename, content_type or "", data)


def fetch_url(url: str) -> NormalizedSource:
    return UrlAdapter().fetch(url)


def extractor_status() -> dict[str, bool]:
    """Reported by /api/health so the UI can explain missing capabilities."""
    return {"text": True, "url": True, "pdf": pdf_available(), "docx": docx_available(), "ocr": ocr_available()}
