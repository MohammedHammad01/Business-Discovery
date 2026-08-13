"""Adapter + normalization unit tests (no network, no AI)."""

from __future__ import annotations

import pytest

from app.schemas.canonical import SourceType
from app.services.ingestion.base import IngestionError
from app.services.ingestion.registry import extract_file, select_adapter
from app.services.ingestion.text_adapter import TextAdapter
from app.services.ingestion.url_adapter import _validate_url
from app.services.normalization.classifier import classify_text, normalize_whatsapp, truncate

WHATSAPP = """\
12/03/2026, 09:14 - Messages and calls are end-to-end encrypted.
12/03/2026, 09:15 - Priya Nair: approvals are taking 2 days
12/03/2026, 09:16 - Ravi Menon: I keep chasing finance on email
12/03/2026, 09:17 - Priya Nair: <Media omitted>
12/03/2026, 09:18 - Ravi Menon: we need one place to see the status
"""

TRANSCRIPT = """\
[00:00:12] Anita Rao: Let's walk through how purchase requests work today.
[00:00:30] Sam Fisher: The requester emails the manager with the details.
[00:01:02] Anita Rao: And then finance re-keys it into the spreadsheet.
[00:01:20] Sam Fisher: Yes, and nobody knows the status without asking.
"""


def test_whatsapp_export_is_detected():
    assert classify_text("client-chat.txt", WHATSAPP) is SourceType.whatsapp_export


def test_transcript_is_detected():
    assert classify_text("meeting-1.txt", TRANSCRIPT) is SourceType.meeting_transcript


def test_whatsapp_normalization_drops_system_lines():
    cleaned = normalize_whatsapp(WHATSAPP)
    assert "end-to-end encrypted" not in cleaned
    assert "<Media omitted>" not in cleaned
    assert "approvals are taking 2 days" in cleaned


def test_text_adapter_produces_normalized_source():
    normalized = TextAdapter().extract("meeting-1.txt", "text/plain", TRANSCRIPT.encode())
    assert normalized.source_type is SourceType.meeting_transcript
    assert normalized.metadata["extraction"] == "plain-text"
    assert "purchase requests" in normalized.content


def test_empty_file_is_rejected():
    with pytest.raises(IngestionError):
        extract_file("empty.txt", "text/plain", b"")


def test_unsupported_extension_is_rejected():
    with pytest.raises(IngestionError):
        select_adapter("archive.zip", "application/zip")


def test_truncate_marks_truncation():
    content, was_truncated = truncate("x" * 500, 100)
    assert was_truncated
    assert "truncated" in content
    assert len(content) < 500


@pytest.mark.parametrize("url", ["ftp://example.com", "http://localhost:8000", "http://127.0.0.1/admin", ""])
def test_unsafe_urls_are_rejected(url):
    with pytest.raises(IngestionError):
        _validate_url(url)
