"""Deterministic offline stand-in for the Discovery Agent.

Used when no ``GEMINI_API_KEY`` is configured, and by the test suite so that
automated tests never call a real model. It is keyword-driven, not intelligent:
it mines real sentences out of the canonical input so the end-to-end flow and
the traceability UI can be demonstrated without a provider, and it says plainly
in `assumptions` that the analysis was generated offline.
"""

from __future__ import annotations

import re

from app.schemas.canonical import CanonicalInput, CanonicalSource
from app.schemas.discovery import (
    BusinessNeed,
    Contradiction,
    CurrentProcess,
    DiscoveryOutput,
    MissingInformation,
    PainPoint,
    PocDefinition,
    PocField,
    ProcessStep,
    RecommendedProcess,
    Requirement,
    Solution,
    SolutionScreen,
    WorkflowStage,
)

MOCK_NOTICE = (
    "This analysis was generated offline by the deterministic mock agent because no "
    "GEMINI_API_KEY was configured. Set the key and re-run Analyze for a real AI analysis."
)

_PAIN_WORDS = (
    "delay", "delays", "slow", "manual", "chase", "chasing", "follow up", "follow-up",
    "missing", "duplicate", "error", "mistake", "rework", "stuck", "waiting", "no visibility",
    "spreadsheet", "email", "lost", "unclear", "bottleneck", "backlog", "complain",
)
_REQ_WORDS = ("need", "needs", "want", "should", "must", "require", "expect", "would like")
_ACTOR_PATTERN = re.compile(r"\b(manager|approver|admin(?:istrator)?|employee|requester|finance|"
                            r"procurement|supervisor|director|customer|client|operator|analyst)\b", re.I)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip(" -\t") for p in parts if 25 <= len(p.strip()) <= 260]


def _hits(sources: list[CanonicalSource], words: tuple[str, ...], limit: int) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for source in sources:
        for sentence in _sentences(source.content):
            lowered = sentence.lower()
            if any(w in lowered for w in words):
                key = lowered[:60]
                if key in seen:
                    continue
                seen.add(key)
                found.append((sentence, source.source_id))
                if len(found) >= limit:
                    return found
    return found


def _actors(sources: list[CanonicalSource]) -> list[str]:
    counts: dict[str, int] = {}
    for source in sources:
        for match in _ACTOR_PATTERN.findall(source.content):
            key = match.strip().title()
            counts[key] = counts.get(key, 0) + 1
    ranked = sorted(counts, key=lambda k: -counts[k])[:5]
    return ranked or ["Requester", "Approver"]


def build(canonical_input: CanonicalInput) -> DiscoveryOutput:
    sources = canonical_input.sources
    all_ids = [s.source_id for s in sources]
    actors = _actors(sources)
    primary, approver = actors[0], (actors[1] if len(actors) > 1 else "Manager")

    pain_hits = _hits(sources, _PAIN_WORDS, 6)
    req_hits = _hits(sources, _REQ_WORDS, 6)

    pain_points = [
        PainPoint(
            problem=sentence,
            impact="Adds manual effort and delay to the process as described in the source.",
            severity="high" if idx < 2 else "medium",
            evidence_source_ids=[source_id],
        )
        for idx, (sentence, source_id) in enumerate(pain_hits)
    ] or [
        PainPoint(
            problem="No explicit pain point keywords were detected in the supplied sources.",
            impact="The current process friction needs to be confirmed with the client.",
            severity="low",
            evidence_source_ids=all_ids,
        )
    ]

    requirements = [
        Requirement(
            requirement=sentence,
            priority="high" if idx < 2 else "medium",
            confidence="fact",
            source_ids=[source_id],
        )
        for idx, (sentence, source_id) in enumerate(req_hits)
    ]

    return DiscoveryOutput(
        business_need=BusinessNeed(
            summary=(
                "Consolidate the process described across "
                f"{len(sources)} client source(s) into a single tracked workflow with clear "
                "ownership and status visibility."
            ),
            goals=[
                "Replace manual coordination with one tracked request flow",
                "Give every participant visible status without chasing",
                "Keep an auditable record of who decided what and when",
            ],
            source_ids=all_ids,
        ),
        current_process=CurrentProcess(
            summary="Reconstructed from the supplied sources; confirm with the client before build.",
            steps=[
                ProcessStep(step=f"{primary} raises the request informally", actor=primary,
                            pain="No standard format", source_ids=all_ids[:1]),
                ProcessStep(step="Details are exchanged over email/chat", actor=primary,
                            pain="Context is spread across channels", source_ids=all_ids),
                ProcessStep(step=f"{approver} reviews and decides", actor=approver,
                            pain="No queue or reminder", source_ids=all_ids[-1:]),
                ProcessStep(step="Outcome is communicated manually", actor=approver,
                            pain="Status is invisible until someone asks", source_ids=all_ids),
            ],
            actors=actors,
            systems=["Email", "Chat", "Spreadsheets"],
        ),
        pain_points=pain_points,
        requirements=requirements,
        missing_information=[
            MissingInformation(
                question="What is the expected turnaround time (SLA) for a decision?",
                reason="No target duration is stated in the supplied sources.",
            ),
            MissingInformation(
                question="How many requests are handled per week, and by how many approvers?",
                reason="Volume determines whether routing rules and a queue view are needed.",
            ),
            MissingInformation(
                question="Which system of record must the outcome be written back to?",
                reason="No integration target is named in the sources.",
            ),
        ],
        contradictions=[
            Contradiction(
                description="Not evaluated by the offline mock agent.",
                source_ids=[],
            )
        ]
        if len(sources) > 1
        else [],
        recommended_process=RecommendedProcess(
            summary="One request record, routed automatically, visible to everyone involved.",
            steps=[
                ProcessStep(step="Submit a structured request via a form", actor=primary,
                            pain="", source_ids=all_ids),
                ProcessStep(step="Route automatically to the right approver", actor="System",
                            pain="", source_ids=all_ids),
                ProcessStep(step="Approve or reject with a reason", actor=approver,
                            pain="", source_ids=all_ids),
                ProcessStep(step="Notify the requester and record the audit trail", actor="System",
                            pain="", source_ids=all_ids),
            ],
            automation_opportunities=[
                "Automatic routing based on request type and amount",
                "Reminders on pending items past the agreed SLA",
                "Status dashboard replacing follow-up messages",
                "Immutable audit trail generated as a side effect of the workflow",
            ],
        ),
        solution=Solution(
            summary="A lightweight request-and-approval application with a shared status view.",
            features=[
                "Structured request form",
                "Automatic approver routing",
                "Approve / reject with reason",
                "Status timeline per request",
                "Notifications on state change",
                "Audit trail export",
            ],
            roles=[primary, approver, "Administrator"],
            modules=["Requests", "Approvals", "Notifications", "Audit"],
            screens=[
                SolutionScreen(name="New Request", purpose="Capture a complete request in one form",
                               primary_role=primary),
                SolutionScreen(name="My Requests", purpose="Track status without chasing anyone",
                               primary_role=primary),
                SolutionScreen(name="Approval Queue", purpose="Decide on pending items in one place",
                               primary_role=approver),
                SolutionScreen(name="Audit Log", purpose="Show who decided what and when",
                               primary_role="Administrator"),
            ],
            workflow=[
                WorkflowStage(stage="Submitted", actor=primary, action="Completes and submits the request",
                              outcome="Request is created and routed"),
                WorkflowStage(stage="In Review", actor=approver, action="Reviews the request details",
                              outcome="Request awaits a decision"),
                WorkflowStage(stage="Decided", actor=approver, action="Approves or rejects with a reason",
                              outcome="Decision is recorded"),
                WorkflowStage(stage="Closed", actor="System", action="Notifies the requester",
                              outcome="Everyone can see the final status"),
            ],
        ),
        poc=PocDefinition(
            objective="Show one request travelling from submission to a recorded decision.",
            screens=["New Request", "Approval Queue", "Status Timeline"],
            demo_flow=[
                f"{primary} submits a request",
                "Request appears in the approval queue",
                f"{approver} approves or rejects with a reason",
                "Requester sees the updated status and audit trail",
            ],
            request_fields=[
                PocField(label="Request title", field_type="text", required=True),
                PocField(label="Category", field_type="select",
                         options=["Purchase", "Access", "Time off", "Other"], required=True),
                PocField(label="Amount", field_type="number", required=False),
                PocField(label="Needed by", field_type="date", required=False),
                PocField(label="Justification", field_type="textarea", required=True),
            ],
            in_scope=["Single happy path", "In-memory state", "One request at a time"],
            out_of_scope=["Authentication", "Real notifications", "Integrations", "Reporting"],
        ),
        assumptions=[
            MOCK_NOTICE,
            "All participants have access to a shared internal application.",
            "One approval level is enough for the POC scenario.",
        ],
    )
