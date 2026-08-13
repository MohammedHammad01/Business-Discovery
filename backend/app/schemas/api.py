"""Request/response models for the HTTP boundary."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.canonical import CanonicalInput, SourceMetadata, SourceType
from app.schemas.discovery import DiscoveryOutput
from app.schemas.poc import PocBlueprint


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    client_name: str = ""
    description: str = ""

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Project name cannot be empty.")
        return v


class ProjectRead(BaseModel):
    project_id: str
    name: str
    client_name: str
    description: str
    created_at: datetime
    source_count: int = 0
    has_analysis: bool = False


class UrlSourceCreate(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class SourceRead(BaseModel):
    source_id: str
    type: SourceType
    name: str
    char_count: int
    preview: str
    metadata: SourceMetadata
    created_at: datetime


class AnalysisRead(BaseModel):
    analysis_id: str
    project_id: str
    created_at: datetime
    model: str
    mocked: bool
    canonical_input: CanonicalInput
    discovery: DiscoveryOutput
    poc_blueprint: PocBlueprint


class HealthRead(BaseModel):
    status: str
    ai_configured: bool
    mock_enabled: bool
    model: str
    extractors: dict[str, bool]
