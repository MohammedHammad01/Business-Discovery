"""Thin wrapper around the Google Gemini SDK (`google-genai`).

Keeps every provider detail in one place:
* structured (JSON-schema enforced) completions for the Discovery Agent,
* vision description for screenshots (an *input capability*, not an agent).

The rest of the application never imports `google.genai` directly, and no
orchestration framework sits in between -- this is one API call.
"""

from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import get_settings

TModel = TypeVar("TModel", bound=BaseModel)


class LLMError(Exception):
    """Any failure talking to the model provider."""


class LLMNotConfiguredError(LLMError):
    """No API key configured and mock mode is disabled."""


class LLMClient:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client: Any | None = None

    # -- capability -------------------------------------------------------
    @property
    def configured(self) -> bool:
        return self._settings.ai_configured

    @property
    def model(self) -> str:
        return self._settings.gemini_model

    def _sdk(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.configured:
            raise LLMNotConfiguredError(
                "GEMINI_API_KEY is not set. Add it to backend/.env (get a free key at "
                "https://aistudio.google.com/apikey), or leave ALLOW_MOCK_LLM=true to run "
                "the demo with mock analysis."
            )
        try:
            from google import genai
            from google.genai import types
        except Exception as exc:  # pragma: no cover - environment dependent
            raise LLMError(
                "The `google-genai` package is not installed. Run `pip install google-genai`."
            ) from exc

        self._client = genai.Client(
            api_key=self._settings.gemini_api_key,
            # google-genai expresses the HTTP timeout in milliseconds.
            http_options=types.HttpOptions(timeout=int(self._settings.ai_timeout_seconds * 1000)),
        )
        return self._client

    @staticmethod
    def _config(**kwargs: Any) -> Any:
        from google.genai import types

        return types.GenerateContentConfig(**kwargs)

    # -- structured completion -------------------------------------------
    def complete_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_model: type[TModel],
        temperature: float = 0.2,
    ) -> TModel:
        """Return a validated ``schema_model`` instance.

        Gemini enforces the schema server-side via ``response_schema``; the SDK
        hands back an already-parsed Pydantic object. ``response.text`` is the
        fallback for the rare case where parsing is skipped.
        """
        client = self._sdk()
        try:
            response = client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=self._config(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=schema_model,
                    temperature=temperature,
                ),
            )
        except ValidationError:
            raise
        except Exception as exc:
            raise LLMError(f"The AI request failed: {_describe(exc)}") from exc

        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, schema_model):
            return parsed
        if isinstance(parsed, dict):
            return schema_model.model_validate(parsed)

        raw = getattr(response, "text", None)
        if not raw:
            raise LLMError(
                "The model returned an empty response. This usually means the request was "
                "blocked or the token limit was reached; try fewer or shorter sources."
            )
        return self.validate_json(raw, schema_model)

    @staticmethod
    def validate_json(raw: str, schema_model: type[TModel]) -> TModel:
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            _, _, text = text.partition("\n")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError(f"The AI response was not valid JSON: {exc}") from exc
        return schema_model.model_validate(payload)

    def complete_text(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        client = self._sdk()
        try:
            response = client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=self._config(system_instruction=system_prompt, temperature=temperature),
            )
        except Exception as exc:
            raise LLMError(f"The AI request failed: {_describe(exc)}") from exc
        return response.text or ""

    # -- vision -----------------------------------------------------------
    def describe_image(self, *, data: bytes, mime_type: str, filename: str) -> str:
        """Gemini Flash is natively multimodal, so this is the same model."""
        client = self._sdk()
        from google.genai import types

        prompt = (
            "Describe this screenshot of a business application or document as plain text "
            "for a business analyst. Transcribe visible labels, fields, columns, statuses, "
            "buttons and numbers exactly. Then note what process step the screen appears to "
            "support. Do not speculate beyond what is visible."
        )
        try:
            response = client.models.generate_content(
                model=self.model,
                contents=[types.Part.from_bytes(data=data, mime_type=mime_type), prompt],
            )
        except Exception as exc:
            raise LLMError(f"Vision extraction failed for '{filename}': {_describe(exc)}") from exc
        return response.text or ""


def _describe(exc: Exception) -> str:
    """Surface the provider's message (quota, key, safety) instead of a bare type."""
    message = getattr(exc, "message", None) or str(exc)
    if "RESOURCE_EXHAUSTED" in message or "429" in message:
        return f"{message} (the Gemini free tier rate limit was hit -- wait a minute and retry)"
    if "API_KEY_INVALID" in message or "401" in message or "403" in message:
        return f"{message} (check GEMINI_API_KEY in backend/.env)"
    return message


_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
