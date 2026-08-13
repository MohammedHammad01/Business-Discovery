"""PDF adapter (PyMuPDF). The dependency is imported lazily so the app still
starts -- and every other adapter still works -- when no wheel is available."""

from __future__ import annotations

from app.schemas.canonical import SourceType
from app.services.ingestion.base import (
    ExtractorUnavailableError,
    IngestionError,
    NormalizedSource,
    extension,
)
from app.services.normalization.classifier import normalize_plain_text


def pdf_available() -> bool:
    try:
        import fitz  # noqa: F401
    except Exception:
        return False
    return True


class PdfAdapter:
    name = "pdf"

    def supports(self, filename: str, content_type: str) -> bool:
        return extension(filename) == "pdf" or content_type == "application/pdf"

    def extract(self, filename: str, content_type: str, data: bytes) -> NormalizedSource:
        try:
            import fitz
        except Exception as exc:  # pragma: no cover - environment dependent
            raise ExtractorUnavailableError(
                "PDF extraction needs PyMuPDF. Install it with `pip install PyMuPDF`, "
                "or upload the document as TXT/DOCX."
            ) from exc

        try:
            with fitz.open(stream=data, filetype="pdf") as doc:
                page_count = doc.page_count
                pages = [page.get_text("text") for page in doc]
        except Exception as exc:
            raise IngestionError(f"Could not read '{filename}' as a PDF: {exc}") from exc

        content = normalize_plain_text("\n\n".join(pages))
        if not content.strip():
            raise IngestionError(
                f"'{filename}' has no extractable text (it may be a scanned image). "
                "Upload it as a screenshot instead so it goes through vision extraction."
            )

        return NormalizedSource(
            source_type=SourceType.pdf,
            name=filename,
            content=content,
            metadata={"extraction": "pymupdf", "page_count": page_count, "content_type": content_type},
        )
