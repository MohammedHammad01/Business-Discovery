"""Discovery output contract -- the only thing the AI agent is allowed to return.

Design notes
------------
* Every field is a concrete model (no free-form ``dict``) so the schema can be
  enforced with OpenAI structured outputs and rendered deterministically by the
  frontend.
* No ``Optional`` / union types: strict JSON-schema mode does not like them and
  the frontend does not need to null-check.
* Traceability is carried by ``*source_ids`` fields that point back at
  ``CanonicalSource.source_id``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Priority = Literal["high", "medium", "low"]
Confidence = Literal["fact", "inference", "assumption"]


class BusinessNeed(BaseModel):
    summary: str = ""
    goals: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class ProcessStep(BaseModel):
    step: str = ""
    actor: str = ""
    pain: str = Field(default="", description="Known friction at this step, or empty.")
    source_ids: list[str] = Field(default_factory=list)


class CurrentProcess(BaseModel):
    summary: str = ""
    steps: list[ProcessStep] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    systems: list[str] = Field(default_factory=list)


class PainPoint(BaseModel):
    problem: str = ""
    impact: str = ""
    severity: Priority = "medium"
    evidence_source_ids: list[str] = Field(default_factory=list)


class Requirement(BaseModel):
    requirement: str = ""
    priority: Priority = "medium"
    confidence: Confidence = "fact"
    source_ids: list[str] = Field(default_factory=list)


class MissingInformation(BaseModel):
    question: str = ""
    reason: str = ""


class Contradiction(BaseModel):
    description: str = ""
    source_ids: list[str] = Field(default_factory=list)


class RecommendedProcess(BaseModel):
    summary: str = ""
    steps: list[ProcessStep] = Field(default_factory=list)
    automation_opportunities: list[str] = Field(default_factory=list)


class SolutionScreen(BaseModel):
    name: str = ""
    purpose: str = ""
    primary_role: str = ""


class WorkflowStage(BaseModel):
    stage: str = ""
    actor: str = ""
    action: str = ""
    outcome: str = ""


class Solution(BaseModel):
    summary: str = ""
    features: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)
    screens: list[SolutionScreen] = Field(default_factory=list)
    workflow: list[WorkflowStage] = Field(default_factory=list)


class PocField(BaseModel):
    """One input on the POC's request form. Rendered deterministically."""

    label: str = ""
    field_type: Literal["text", "textarea", "number", "select", "date"] = "text"
    options: list[str] = Field(default_factory=list)
    required: bool = True


class PocDefinition(BaseModel):
    objective: str = ""
    screens: list[str] = Field(default_factory=list)
    demo_flow: list[str] = Field(default_factory=list)
    request_fields: list[PocField] = Field(default_factory=list)
    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)


class DiscoveryOutput(BaseModel):
    business_need: BusinessNeed = Field(default_factory=BusinessNeed)
    current_process: CurrentProcess = Field(default_factory=CurrentProcess)
    pain_points: list[PainPoint] = Field(default_factory=list)
    requirements: list[Requirement] = Field(default_factory=list)
    missing_information: list[MissingInformation] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    recommended_process: RecommendedProcess = Field(default_factory=RecommendedProcess)
    solution: Solution = Field(default_factory=Solution)
    poc: PocDefinition = Field(default_factory=PocDefinition)
    assumptions: list[str] = Field(default_factory=list)
