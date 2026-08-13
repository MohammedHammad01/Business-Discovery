"""POC blueprint.

Derived *deterministically* from the validated ``DiscoveryOutput`` -- no second
AI call, no AI-generated frontend code. The React POC page renders this shape
with fixed components.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.discovery import PocField


class PocStage(BaseModel):
    key: str
    title: str
    actor: str
    action: str
    outcome: str
    status_label: str


class PocBlueprint(BaseModel):
    objective: str = ""
    entity_label: str = "Request"
    roles: list[str] = Field(default_factory=list)
    request_fields: list[PocField] = Field(default_factory=list)
    stages: list[PocStage] = Field(default_factory=list)
    demo_flow: list[str] = Field(default_factory=list)
    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
