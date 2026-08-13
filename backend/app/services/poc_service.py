"""Builds the interactive POC blueprint from a validated DiscoveryOutput.

Deterministic on purpose: the AI decides *what the application should do*; this
module decides *what the demo renders*. No AI-generated frontend code.
"""

from __future__ import annotations

import re

from app.schemas.discovery import DiscoveryOutput, PocField, WorkflowStage
from app.schemas.poc import PocBlueprint, PocStage

_DEFAULT_FIELDS = [
    PocField(label="Title", field_type="text", required=True),
    PocField(label="Details", field_type="textarea", required=True),
]

_STATUS_BY_KEYWORD = (
    (("submit", "create", "raise", "request", "draft"), "Submitted"),
    (("review", "check", "verify", "assess", "triage"), "In review"),
    (("approve", "decide", "sign", "authorise", "authorize"), "Decided"),
    (("notify", "close", "complete", "archive", "record"), "Closed"),
)


def _slug(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def _status_label(stage: WorkflowStage) -> str:
    if stage.stage.strip():
        return stage.stage.strip()
    text = f"{stage.action} {stage.outcome}".lower()
    for keywords, label in _STATUS_BY_KEYWORD:
        if any(k in text for k in keywords):
            return label
    return "In progress"


def _entity_label(discovery: DiscoveryOutput) -> str:
    """Name the thing that flows through the POC, using the client's own words."""
    haystack = " ".join(
        [discovery.poc.objective, discovery.solution.summary, discovery.business_need.summary]
        + discovery.solution.modules
    ).lower()
    for candidate in ("request", "approval", "order", "ticket", "case", "claim", "application", "invoice", "quote"):
        if candidate in haystack:
            return candidate.title()
    return "Request"


def _fallback_stages(discovery: DiscoveryOutput) -> list[PocStage]:
    """If the model gave no workflow, derive stages from the demo flow."""
    roles = discovery.solution.roles or ["Requester", "Approver"]
    steps = discovery.poc.demo_flow or [s.step for s in discovery.recommended_process.steps]
    stages: list[PocStage] = []
    for index, step in enumerate(steps[:6]):
        actor = roles[min(index, len(roles) - 1)]
        stages.append(
            PocStage(
                key=_slug(step, f"stage-{index + 1}"),
                title=step,
                actor=actor,
                action=step,
                outcome="",
                status_label=_status_label(WorkflowStage(stage="", actor=actor, action=step, outcome="")),
            )
        )
    return stages


def build_blueprint(discovery: DiscoveryOutput) -> PocBlueprint:
    stages: list[PocStage] = []
    for index, stage in enumerate(discovery.solution.workflow[:6]):
        title = stage.stage or stage.action or f"Step {index + 1}"
        stages.append(
            PocStage(
                key=_slug(title, f"stage-{index + 1}"),
                title=title,
                actor=stage.actor or "Participant",
                action=stage.action,
                outcome=stage.outcome,
                status_label=_status_label(stage),
            )
        )

    if not stages:
        stages = _fallback_stages(discovery)

    # Keys feed React list keys and the client-side state machine; force uniqueness.
    seen: dict[str, int] = {}
    for stage in stages:
        count = seen.get(stage.key, 0) + 1
        seen[stage.key] = count
        if count > 1:
            stage.key = f"{stage.key}-{count}"

    fields = discovery.poc.request_fields or _DEFAULT_FIELDS
    return PocBlueprint(
        objective=discovery.poc.objective or discovery.solution.summary,
        entity_label=_entity_label(discovery),
        roles=discovery.solution.roles,
        request_fields=fields,
        stages=stages,
        demo_flow=discovery.poc.demo_flow,
        in_scope=discovery.poc.in_scope,
        out_of_scope=discovery.poc.out_of_scope,
    )
