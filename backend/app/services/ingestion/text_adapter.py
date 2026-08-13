"""TXT / MD / transcript / WhatsApp export adapter."""

from __future__ import annotations

from app.schemas.canonical import SourceType
from app.services.ingestion.base import (
    IngestionError,
    NormalizedSource,
    decode_text,
    extension,
)
from app.services.normalization.classifier import (
    classify_text,
    normalize_plain_text,
    normalize_whatsapp,
)

EXTENSIONS = {"txt", "md", "log", "vtt", "srt", "csv"}


class TextAdapter:
    name = "text"

    def supports(self, filename: str, content_type: str) -> bool:
        return extension(filename) in EXTENSIONS or content_type.startswith("text/")

    def extract(self, filename: str, content_type: str, data: bytes) -> NormalizedSource:
        raw = decode_text(data)
        if not raw.strip():
            raise IngestionError(f"'{filename}' contains no readable text.")

        source_type = classify_text(filename, raw)
        content = (
            normalize_whatsapp(raw)
            if source_type is SourceType.whatsapp_export
            else normalize_plain_text(raw)
        )
        return NormalizedSource(
            source_type=source_type,
            name=filename,
            content=content,
            metadata={"extraction": "plain-text", "content_type": content_type},
        )
