"""Agent contract, schema validation and deterministic POC-blueprint tests."""

from __future__ import annotations

import pytest

from app.schemas.canonical import CanonicalInput, CanonicalSource, SourceType
from app.schemas.discovery import DiscoveryOutput, Solution, WorkflowStage
from app.services.discovery_agent import BusinessDiscoveryAgent, DiscoveryAgentError
from app.services.llm_client import LLMClient
from app.services.poc_service import build_blueprint

CANONICAL = CanonicalInput(
    project_id="p1",
    sources=[
        CanonicalSource(
            source_id="src-001",
            type=SourceType.meeting_transcript,
            name="meeting-1.txt",
            content=(
                "Anita Rao: The requester emails the manager and then waits. "
                "Sam Fisher: Approvals are slow because finance has to chase people on email. "
                "Anita Rao: We need one place where the status is visible to everyone."
            ),
        )
    ],
)


def test_agent_returns_valid_discovery_without_a_provider():
    result = BusinessDiscoveryAgent().run(CANONICAL, project_name="Approvals")
    assert result.mocked is True
    DiscoveryOutput.model_validate(result.discovery.model_dump())
    assert result.discovery.business_need.summary
    assert result.discovery.pain_points


def test_agent_rejects_an_empty_project():
    with pytest.raises(DiscoveryAgentError):
        BusinessDiscoveryAgent().run(CanonicalInput(project_id="p1", sources=[]))


def test_agent_rejects_oversized_input(monkeypatch):
    agent = BusinessDiscoveryAgent()
    monkeypatch.setattr(agent._settings, "max_total_content_chars", 10)
    with pytest.raises(DiscoveryAgentError, match="over the"):
        agent.run(CANONICAL)


def test_pain_points_cite_their_sources():
    discovery = BusinessDiscoveryAgent().run(CANONICAL).discovery
    known = {s.source_id for s in CANONICAL.sources}
    for pain in discovery.pain_points:
        assert set(pain.evidence_source_ids) <= known


def test_malformed_ai_json_is_rejected():
    from app.services.llm_client import LLMError

    with pytest.raises(LLMError):
        LLMClient.validate_json("not json at all", DiscoveryOutput)


def test_json_in_a_markdown_fence_is_still_parsed():
    parsed = LLMClient.validate_json('```json\n{"assumptions": ["a"]}\n```', DiscoveryOutput)
    assert parsed.assumptions == ["a"]


def test_blueprint_is_derived_from_the_workflow():
    discovery = DiscoveryOutput(
        solution=Solution(
            roles=["Requester", "Manager"],
            workflow=[
                WorkflowStage(stage="Submitted", actor="Requester", action="Submits", outcome="Created"),
                WorkflowStage(stage="Approved", actor="Manager", action="Approves", outcome="Recorded"),
            ],
        )
    )
    blueprint = build_blueprint(discovery)
    assert [s.title for s in blueprint.stages] == ["Submitted", "Approved"]
    assert len({s.key for s in blueprint.stages}) == 2
    assert blueprint.request_fields, "a POC always needs at least a fallback form"


def test_blueprint_falls_back_to_the_demo_flow():
    discovery = DiscoveryOutput()
    discovery.poc.demo_flow = ["Employee creates a request", "Manager approves the request"]
    blueprint = build_blueprint(discovery)
    assert len(blueprint.stages) == 2
    assert blueprint.stages[0].status_label == "Submitted"
