"""Website adapter.

Fetches an accessible page and extracts readable text. It deliberately does not
clone or crawl the site -- the goal is to understand the existing system, not
reproduce it.

Basic SSRF protection: http/https only, no credentials in the URL, and private
/ loopback / link-local hosts are refused.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse, urlunparse

import httpx

from app.config import get_settings
from app.schemas.canonical import SourceType
from app.services.ingestion.base import IngestionError, NormalizedSource
from app.services.normalization.classifier import normalize_plain_text

_MAX_BYTES = 2 * 1024 * 1024
_STRIP_TAGS = ("script", "style", "noscript", "svg", "iframe", "template")


def _validate_url(raw: str) -> str:
    candidate = raw.strip()
    if not candidate:
        raise IngestionError("The URL is empty.")
    if "://" not in candidate:
        candidate = f"https://{candidate}"

    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https"):
        raise IngestionError("Only http:// and https:// URLs are supported.")
    if not parsed.hostname:
        raise IngestionError(f"'{raw}' is not a valid URL.")
    if parsed.username or parsed.password:
        raise IngestionError("URLs with embedded credentials are not allowed.")

    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise IngestionError(f"Could not resolve host '{parsed.hostname}': {exc}") from exc

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise IngestionError("Fetching internal/private network addresses is not allowed.")

    return urlunparse(parsed)


def _html_to_text(html: str) -> tuple[str, str]:
    """Return (title, text). Falls back to a crude strip if bs4 is missing."""
    try:
        from bs4 import BeautifulSoup
    except Exception:  # pragma: no cover - environment dependent
        import re

        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        return "", normalize_plain_text(re.sub(r"[ \t]{2,}", " ", text))

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(list(_STRIP_TAGS)):
        tag.decompose()
    title = soup.title.get_text(strip=True) if soup.title else ""
    text = soup.get_text(separator="\n")
    lines = [ln.strip() for ln in text.splitlines()]
    return title, normalize_plain_text("\n".join(ln for ln in lines if ln))


class UrlAdapter:
    name = "url"

    def fetch(self, url: str) -> NormalizedSource:
        settings = get_settings()
        target = _validate_url(url)

        try:
            with httpx.Client(
                timeout=settings.url_fetch_timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": "ai-business-discovery/1.0 (+POC)"},
            ) as client:
                response = client.get(target)
                response.raise_for_status()
                body = response.content[:_MAX_BYTES]
                final_url = str(response.url)
                content_type = response.headers.get("content-type", "")
        except httpx.HTTPStatusError as exc:
            raise IngestionError(
                f"The site returned HTTP {exc.response.status_code} for {target}."
            ) from exc
        except httpx.HTTPError as exc:
            raise IngestionError(f"Could not fetch {target}: {exc}") from exc

        charset = "utf-8"
        if "charset=" in content_type:
            charset = content_type.split("charset=")[-1].split(";")[0].strip() or "utf-8"
        html = body.decode(charset, errors="replace")

        title, text = _html_to_text(html)
        if not text.strip():
            raise IngestionError(
                f"No readable text was found at {target}. The page may be rendered entirely "
                "client-side; upload a screenshot of it instead."
            )

        return NormalizedSource(
            source_type=SourceType.website,
            name=title or urlparse(final_url).netloc or final_url,
            content=text,
            metadata={"extraction": "html", "url": final_url, "content_type": content_type},
        )
