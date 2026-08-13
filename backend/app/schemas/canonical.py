"""Canonical input contract.

Every client input -- PDF, transcript, WhatsApp export, screenshot, website --
is normalized into this shape before the AI layer sees it. This is the single
most important contract in the system: the Discovery Agent is format-agnostic
because it only ever reads `CanonicalInput`.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    meeting_transcript = "meeting_transcript"
    whatsapp_export = "whatsapp_export"
    document = "document"
    pdf = "pdf"
    docx = "docx"
    text = "text"
    screenshot = "screenshot"
    website = "website"


class SourceMetadata(BaseModel):
    page_count: int | None = None
    url: str | None = None
    original_filename: str | None = None
    content_type: str | None = None
    char_count: int | None = None
    truncated: bool = False
    extraction: str | None = Field(
        default=None,
        description="How the text was produced, e.g. 'pymupdf', 'vision', 'plain-text'.",
    )
    uploaded_at: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class CanonicalSource(BaseModel):
    source_id: str
    type: SourceType
    name: str
    content: str
    metadata: SourceMetadata = Field(default_factory=SourceMetadata)


class CanonicalInput(BaseModel):
    project_id: str
    sources: list[CanonicalSource] = Field(default_factory=list)

    def total_chars(self) -> int:
        return sum(len(s.content) for s in self.sources)
