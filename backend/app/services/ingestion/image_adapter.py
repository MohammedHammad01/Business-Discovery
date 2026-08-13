"""Screenshot adapter.

Vision is an *input capability*, not a second agent: the description it
produces is stored as ordinary text in the same canonical source schema, and
the Business Discovery Agent never learns that it came from an image.

Order of preference: multimodal description -> local OCR (pytesseract) ->
clear error telling the user what to do instead.
"""

from __future__ import annotations

from app.schemas.canonical import SourceType
from app.services.ingestion.base import (
    IngestionError,
    NormalizedSource,
    extension,
)
from app.services.llm_client import LLMError, get_llm_client

EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "bmp"}
_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
    "bmp": "image/bmp",
}


def ocr_available() -> bool:
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
    except Exception:
        return False
    return True


def _ocr(data: bytes) -> str:
    import io

    import pytesseract
    from PIL import Image

    return pytesseract.image_to_string(Image.open(io.BytesIO(data)))


class ImageAdapter:
    name = "image"

    def supports(self, filename: str, content_type: str) -> bool:
        return extension(filename) in EXTENSIONS or content_type.startswith("image/")

    def extract(self, filename: str, content_type: str, data: bytes) -> NormalizedSource:
        mime = content_type if content_type.startswith("image/") else _MIME.get(extension(filename), "image/png")

        client = get_llm_client()
        errors: list[str] = []

        if client.configured:
            try:
                text = client.describe_image(data=data, mime_type=mime, filename=filename)
                if text.strip():
                    return self._source(filename, text, "vision", mime)
            except LLMError as exc:
                errors.append(str(exc))

        if ocr_available():
            try:
                text = _ocr(data)
                if text.strip():
                    return self._source(filename, text, "ocr", mime)
                errors.append("OCR found no readable text in the image.")
            except Exception as exc:
                errors.append(f"OCR failed: {exc}")

        detail = " ".join(errors) if errors else (
            "No vision model is configured (set GEMINI_API_KEY) and pytesseract is not installed."
        )
        raise IngestionError(f"Could not extract text from '{filename}'. {detail}")

    @staticmethod
    def _source(filename: str, text: str, extraction: str, mime: str) -> NormalizedSource:
        return NormalizedSource(
            source_type=SourceType.screenshot,
            name=filename,
            content=text.strip(),
            metadata={"extraction": extraction, "content_type": mime},
        )
