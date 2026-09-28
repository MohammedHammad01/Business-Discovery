"""Application settings. Secrets come from the environment / .env only."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- AI ---------------------------------------------------------------
    # Google AI Studio (Gemini). The free tier is enough for this POC.
    # Get a key at https://aistudio.google.com/apikey
    gemini_api_key: str = ""
    # gemini-2.5-flash is multimodal, supports structured output, and is on the
    # free tier. gemini-2.0-flash / gemini-2.5-flash-lite also work.
    gemini_model: str = "gemini-2.5-flash"
    ai_timeout_seconds: float = 120.0

    # When no API key is configured the Discovery Agent falls back to a
    # deterministic mock so the end-to-end flow (and the test suite) still runs.
    allow_mock_llm: bool = True so we can use without llm also

    # --- Storage ----------------------------------------------------------
    database_url: str = "sqlite:///./app.db"

    # --- Limits -----------------------------------------------------------
    max_upload_bytes: int = 5 * 1024 * 1024          # 5 MB per file
    max_source_chars: int = 60_000                   # per normalized source
    max_total_content_chars: int = 160_000           # whole canonical input
    url_fetch_timeout_seconds: float = 15.0

    # --- Web --------------------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ai_configured(self) -> bool:
        return bool(self.gemini_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
