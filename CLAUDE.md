# CLAUDE.md — AI Business Discovery to POC

Guidance for anyone (human or AI) working in this repository.

## 1. Assignment context

A small working application that accepts scattered client information and turns it into:

1. A structured understanding of the business need
2. Pain points and current-process analysis
3. Missing/unclear information
4. Practical process improvements
5. A proposed application solution
6. A small interactive POC

Inputs may be meeting transcripts, call notes, WhatsApp exports, PDFs, documents,
screenshots, or a website reference. Direct Teams/WhatsApp integrations are **not**
required — uploaded/exported sample data is acceptable.

The scope is intentionally a POC, not a production system.

## 2. Core architecture principle

**Use the minimum number of AI agents possible.** Do not build a multi-agent system
just for demonstration.

```text
Frontend (React)
      ↓
FastAPI backend — upload / URL ingestion, validation, normalization
      ↓
Canonical Input JSON — same schema for EVERY input source
      ↓
ONE AI Business Analyst Agent — understand → analyze → recommend → solution outline
      ↓
Structured Discovery JSON
      ↓
POC Renderer — deterministic UI from JSON
```

There is **one** agent, not separate agents for requirement extraction, pain-point
analysis, solution architecture, feature generation or POC generation. Those are
stages inside one structured Business Discovery Agent
(`backend/app/services/discovery_agent.py`).

Parsing, validation, file extraction, URL fetching, JSON validation and rendering are
ordinary application code.

## 3. Why canonical JSON comes first

Client inputs arrive as PDF, DOCX, TXT, transcript, WhatsApp export, screenshot or
website. Every one of them is converted to the same internal representation
(`backend/app/schemas/canonical.py`) *before* the AI layer sees it:

```json
{
  "project_id": "demo-001",
  "sources": [
    { "source_id": "src-001", "type": "meeting_transcript", "name": "meeting-1.txt",
      "content": "...", "metadata": { "uploaded_at": "2026-08-13T10:00:00Z" } }
  ]
}
```

This is the most important architectural decision. The AI layer must not care whether
information came from WhatsApp, a PDF, a transcript or a screenshot.

## 4. Canonical discovery output

The agent returns strict JSON only (`backend/app/schemas/discovery.py`):
`business_need`, `current_process`, `pain_points`, `requirements`,
`missing_information`, `contradictions`, `recommended_process`, `solution`, `poc`,
`assumptions`.

The frontend renders that structure. It never parses free-form AI text.

## 5. AI agent contract

Input: `CanonicalInput`. Output: `DiscoveryOutput`. Responsibilities:

1. Consolidate information across sources
2. Identify the actual business goal
3. Reconstruct the current process
4. Identify pain points and business impact
5. Extract explicit requirements
6. Infer requirements only when clearly supported
7. Separate assumptions from facts
8. Identify missing information
9. Recommend practical improvements
10. Propose a simple application solution
11. Define a small POC scope
12. Return valid structured JSON

**The agent must never invent facts and present them as client requirements.** Use
`source_ids` for traceability, `assumptions` for inference, `missing_information` for
uncertainty, and `contradictions` where sources disagree.

## 6. Prompting strategy

One strong system prompt, versioned in code (`backend/app/services/prompts.py`,
`PROMPT_VERSION`). Every stored analysis records the prompt version and model that
produced it. Use structured output / JSON-schema enforcement where the model supports
it.

## 7. Input processing

Deterministic adapters in `backend/app/services/ingestion/`:

```text
PDF        -> text extraction (PyMuPDF)
DOCX       -> text extraction (python-docx)
TXT        -> plain text
WhatsApp   -> plain-text normalization (system lines stripped)
Transcript -> plain-text normalization
Image      -> vision description, OCR fallback
URL        -> webpage text extraction
```

Each adapter returns a `NormalizedSource(source_type, name, content, metadata)`; the
service layer assembles them into one `CanonicalInput`.

## 8. Image / screenshot handling

Accept the upload, describe it with a multimodal model (or OCR), store the result as
text in the same canonical schema. **Do not create a separate "Vision Agent"** —
vision is an input capability, not another business agent.

## 9. Website handling

Accept a URL, fetch accessible page content, extract text, normalize it as a
`website` source. Do not clone the site. Only http/https, no private/loopback hosts.

## 10. Backend responsibilities

```text
POST   /api/projects
GET    /api/projects
GET    /api/projects/{id}
POST   /api/projects/{id}/reset
POST   /api/projects/{id}/sources
POST   /api/projects/{id}/sources/url
GET    /api/projects/{id}/sources
DELETE /api/projects/{id}/sources/{source_id}
GET    /api/projects/{id}/canonical-input
POST   /api/projects/{id}/analyze
GET    /api/projects/{id}/discovery
GET    /api/health
```

The backend owns validation, parsing, normalization, canonical JSON construction, AI
invocation, output validation, persistence and API responses.

## 11. Frontend responsibilities

Four simple screens: Input Workspace, Business Discovery, Proposed Solution, POC.
Keep the UI simple; do not spend the budget on visual design.

## 12. POC rendering principle

Do not ask the AI to generate React code. The AI generates structured solution JSON;
`poc_service.py` turns it into a `PocBlueprint`; the frontend renders it with fixed
components (`SolutionPage`, `PocPage`, `primitives.tsx`). Safer, faster, easier to
explain.

## 13. Persistence

SQLite via SQLAlchemy. Tables: `projects`, `sources`, `analyses`. Store the canonical
input JSON and the discovery output JSON for reproducibility. Do not introduce a
heavier database.

## 14. Error handling

Handle unsupported file types, empty files, malformed URLs, extraction failures, AI
timeouts, invalid AI JSON, missing API keys and oversized input. Validate the AI
response against the Pydantic schema; on failure, try structured parsing, then one
deterministic repair retry. Never silently accept malformed output, and **do not
create a second agent to validate the first**.

## 15. Engineering priorities

1. End-to-end working flow
2. Canonical input schema
3. Reliable AI output schema
4. Useful business analysis
5. Simple POC
6. Source traceability
7. Good error handling
8. Clean UI
9. Extra polish

## 16. Technology

Backend: Python, FastAPI, Pydantic, SQLAlchemy, SQLite.
AI: Google Gemini structured output (`google-genai`), one Business Discovery Agent.
Frontend: React, Vite, TypeScript, plain CSS.
Documents: PyMuPDF, python-docx, vision/OCR only where necessary.
Dev: `.env` for secrets, pytest for core tests, Docker optional.

## 17. Repository structure

```text
ai-business-discovery/
├── backend/app/{api,db,models,schemas,services}   services/{ingestion,normalization}
├── backend/tests/
├── frontend/src/{components,pages,services,types}
├── sample_data/
├── docs/{PLAN.md,architecture.md}
├── .env.example
├── docker-compose.yml
└── README.md
```

## 18. Coding rules

- Prefer simple, readable code.
- Keep business logic out of route handlers.
- Use Pydantic models at API boundaries.
- Type important functions.
- Keep AI prompts versioned in code.
- Keep ingestion adapters independent of business analysis.
- Never expose API keys to the frontend.
- Do not hard-code client-specific business logic.
- Keep the canonical JSON schema stable.
- Keep the Discovery Agent stateless between requests.
- Persist input and output for reproducibility.

## 19. What NOT to build

Multi-agent orchestration, autonomous agent loops, vector databases, RAG (unless the
POC genuinely needs retrieval), Kubernetes, event-driven microservices, direct
Teams/WhatsApp integrations, production-grade authentication, elaborate design
systems, AI-generated frontend code, unnecessary cloud infrastructure.

**No LLM framework either.** Do not add LangChain, LangGraph, LlamaIndex or similar.
The system makes one stateless structured call to one model; a framework would add a
dependency and indirection without removing any code. The provider SDK is called
directly from `services/llm_client.py`, which is also what keeps a provider swap to a
single file.

## 20. Demo story

Create project → upload transcript → upload WhatsApp export → upload process document
→ upload screenshot → Analyze → show canonical input → business understanding → pain
points → missing information → improved process → proposed solution → interactive POC
→ explain architecture and tradeoffs.

The message to communicate:

> "I deliberately used one AI Business Discovery Agent. I normalized every input into
> one canonical JSON contract first, so the AI layer is format-agnostic and the
> frontend consumes structured output rather than unreliable free-form text."

## 21. Definition of done

At least three input types work; all inputs become canonical JSON; one AI call
produces structured discovery output; output is validated; business need, current
process, pain points, missing information, improvements and solution outline are all
visible; the POC is interactive; frontend and backend communicate through APIs; the
README explains setup; sample data is included; the demo can be recorded in 5–8
minutes.
