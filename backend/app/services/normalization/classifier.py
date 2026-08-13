"""Deterministic classification + cleanup of plain-text sources.

WhatsApp exports and meeting transcripts are both ``.txt`` files, but knowing
which one it is gives the Discovery Agent useful context, so we detect it with
plain regex rather than an AI call.
"""

from __future__ import annotations

import re

from app.schemas.canonical import SourceType

# 12/03/2026, 09:14 - Priya Nair: ...      (and the [12/03/2026, 09:14:02] variant)
_WHATSAPP_LINE = re.compile(
    r"^\s*\[?\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:[APap]\.?[Mm]\.?)?\]?\s*[-–]?\s*[^:]{1,60}:",
)

# [00:03:11] Speaker:   /   00:03 Speaker:   /   Speaker (Role):
_TRANSCRIPT_LINE = re.compile(
    r"^\s*(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s+)?[A-Z][\w .'-]{1,40}(?:\([^)]{1,40}\))?\s*:",
)

_TRANSCRIPT_HINTS = ("transcript", "meeting", "call", "recording", "minutes", "standup")
_WHATSAPP_HINTS = ("whatsapp", "chat", "wa-export")


def classify_text(filename: str, content: str) -> SourceType:
    lowered = filename.lower()
    lines = [ln for ln in content.splitlines() if ln.strip()][:120]
    if not lines:
        return SourceType.text

    whatsapp_hits = sum(1 for ln in lines if _WHATSAPP_LINE.match(ln))
    speaker_hits = sum(1 for ln in lines if _TRANSCRIPT_LINE.match(ln))

    if whatsapp_hits >= max(3, len(lines) * 0.3):
        return SourceType.whatsapp_export
    if any(h in lowered for h in _WHATSAPP_HINTS) and whatsapp_hits:
        return SourceType.whatsapp_export
    if speaker_hits >= max(3, len(lines) * 0.3):
        return SourceType.meeting_transcript
    if any(h in lowered for h in _TRANSCRIPT_HINTS):
        return SourceType.meeting_transcript
    return SourceType.text


_SYSTEM_NOISE = (
    "Messages and calls are end-to-end encrypted",
    "<Media omitted>",
    "This message was deleted",
    "created group",
    "changed the subject",
    "joined using this group's invite link",
)


def normalize_whatsapp(content: str) -> str:
    """Drop WhatsApp system chatter and collapse the export into speaker lines."""
    kept: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(noise.lower() in stripped.lower() for noise in _SYSTEM_NOISE):
            continue
        kept.append(stripped)
    return "\n".join(kept)


def normalize_plain_text(content: str) -> str:
    """Normalize line endings and squash runs of blank lines."""
    text = content.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def truncate(content: str, limit: int) -> tuple[str, bool]:
    if len(content) <= limit:
        return content, False
    head = content[: int(limit * 0.7)]
    tail = content[-int(limit * 0.25) :]
    return f"{head}\n\n...[content truncated for length]...\n\n{tail}", True
