"""The single AI agent in this system.

CanonicalInput -> one structured LLM call -> validated DiscoveryOutput.

There is deliberately no requirement agent, pain-point agent, solution architect
agent or POC agent. Those are stages inside this one prompt. Everything around
it -- parsing, validation, rendering -- is ordinary application code.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.canonical import CanonicalInput
from app.schemas.discovery import DiscoveryOutput
from app.services import mock_discovery
from app.services.llm_client import LLMClient, LLMError, LLMNotConfiguredError, get_llm_client
from app.services.prompts import (
    PROMPT_VERSION,
    REPAIR_PROMPT_TEMPLATE,
    SYSTEM_PROMPT,
    build_user_prompt,
)


class DiscoveryAgentError(Exception):
    """The agent could not produce a valid DiscoveryOutput."""


@dataclass(slots=True)
class AgentResult:
    discovery: DiscoveryOutput
    model: str
    prompt_version: str
    mocked: bool


class BusinessDiscoveryAgent:
    """Stateless between requests -- everything it needs arrives in the input."""

    def __init__(self, client: LLMClient | None = None) -> None:
        self._client = client or get_llm_client()
        self._settings = get_settings()

    def run(
        self,
        canonical_input: CanonicalInput,
        *,
        project_name: str = "",
        client_name: str = "",
        project_description: str = "",
    ) -> AgentResult:
        if not canonical_input.sources:
            raise DiscoveryAgentError("Add at least one source before running the analysis.")

        total = canonical_input.total_chars()
        if total > self._settings.max_total_content_chars:
            raise DiscoveryAgentError(
                f"The combined sources are {total:,} characters, over the "
                f"{self._settings.max_total_content_chars:,} limit for a single analysis call. "
                "Remove a source or shorten the inputs."
            )

        if not self._client.configured:
            if not self._settings.allow_mock_llm:
                raise DiscoveryAgentError(
                    "GEMINI_API_KEY is not configured and mock mode is disabled."
                )
            return AgentResult(
                discovery=mock_discovery.build(canonical_input),
                model="mock",
                prompt_version=PROMPT_VERSION,
                mocked=True,
            )

        user_prompt = build_user_prompt(
            project_name=project_name,
            client_name=client_name,
            project_description=project_description,
            canonical_json=canonical_input.model_dump_json(indent=2),
        )

        try:
            discovery = self._client.complete_structured(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                schema_model=DiscoveryOutput,
            )
        except ValidationError as exc:
            discovery = self._repair(user_prompt, exc)
        except LLMNotConfiguredError as exc:
            raise DiscoveryAgentError(str(exc)) from exc
        except LLMError as exc:
            raise DiscoveryAgentError(str(exc)) from exc

        return AgentResult(
            discovery=discovery,
            model=self._client.model,
            prompt_version=PROMPT_VERSION,
            mocked=False,
        )

    # -- one deterministic repair attempt, never a "validation agent" ------
    def _repair(self, user_prompt: str, error: ValidationError) -> DiscoveryOutput:
        repair_prompt = REPAIR_PROMPT_TEMPLATE.format(
            errors=str(error)[:4000], previous="(schema-invalid response)"
        )
        try:
            return self._client.complete_structured(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=f"{user_prompt}\n\n{repair_prompt}",
                schema_model=DiscoveryOutput,
                temperature=0.0,
            )
        except (LLMError, ValidationError) as exc:
            raise DiscoveryAgentError(
                "The AI returned output that did not match the discovery schema, and the "
                f"repair attempt also failed: {exc}"
            ) from exc
