"""Adapter contract shared by every ingestion adapter.

Adapters answer exactly one question: *what text can I extract from this
source?* They contain no business analysis logic.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.schemas.canonical import SourceType


class IngestionError(Exception):
    """Raised for any recoverable ingestion problem (surfaced as HTTP 400/422)."""


class ExtractorUnavailableError(IngestionError):
    """A required optional dependency (PyMuPDF, python-docx, ...) is not installed."""


class NormalizedSource(BaseModel):
    source_type: SourceType
    name: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceAdapter(Protocol):
    name: str

    def supports(self, filename: str, content_type: str) -> bool: ...

    def extract(self, filename: str, content_type: str, data: bytes) -> NormalizedSource: ...


def extension(filename: str) -> str:
    _, _, ext = filename.rpartition(".")
    return ext.lower() if "." in filename else ""


def decode_text(data: bytes) -> str:
    """Best-effort decode of a user-supplied text file."""
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")
