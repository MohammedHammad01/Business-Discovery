# AI Business Discovery → POC

Turns scattered client information — meeting transcripts, WhatsApp exports, documents,
screenshots, a website — into a structured business discovery and a small interactive
POC.

## The problem

Client requirements never arrive in one place or one format. Someone has to read a
transcript, a chat export, a procedure PDF and a screenshot of the current system, and
turn all of it into: what does this client actually need, what does their process look
like today, where does it hurt, what is still unknown, and what should we build?

This application does that pass, and renders the result as something you can click
through.

## Architecture

```text
   Transcript   WhatsApp   PDF/DOCX   Screenshot   Website URL
        │           │          │           │            │
        └───────────┴──────────┴─────┬─────┴────────────┘
                                     ▼
                     Deterministic ingestion adapters
                     (PyMuPDF, python-docx, vision/OCR, HTML)
                                     ▼
                      ┌───────────────────────────┐
                      │   Canonical Input JSON     │   ← one contract, every format
                      │   sources[]: source_id,    │
                      │   type, name, content,     │
                      │   metadata                 │
                      └───────────────────────────┘
                                     ▼
                      ┌───────────────────────────┐
                      │  ONE Business Discovery    │   ← the only AI in the system
                      │  Agent (one structured     │
                      │  LLM call per analysis)    │
                      └───────────────────────────┘
                                     ▼
                      ┌───────────────────────────┐
                      │  Discovery Output JSON     │   ← Pydantic-validated
                      │  need · process · pains ·  │
                      │  requirements · gaps ·     │
                      │  improvements · solution · │
                      │  poc · assumptions         │
                      └───────────────────────────┘
                          ▼                    ▼
                  FastAPI responses    Deterministic POC blueprint
                          ▼                    ▼
                      React frontend — discovery, solution, interactive POC
```

### The two decisions that matter

**1. Canonical JSON before AI.** Every source is normalized into the same schema
before the AI layer sees it. The agent is format-agnostic: it never learns whether
text came from a PDF, a chat export or a screenshot. Adding a new input type is an
adapter, not a prompt change.

**2. One agent, not a swarm.** Requirement extraction, pain-point analysis, solution
design and POC scoping are *stages inside one prompt*, not separate agents. One AI
call per analysis means lower latency and cost, no orchestration complexity, and no
inconsistency between agents that each saw a different slice of the input. Everything
that can be deterministic — parsing, validation, traceability, POC rendering — is
ordinary code.

## Tech stack

| Layer     | Choice                                              |
| --------- | --------------------------------------------------- |
| Backend   | Python, FastAPI, Pydantic v2, SQLAlchemy 2, SQLite   |
| AI        | Google Gemini (`google-genai`) structured output, one Discovery Agent |
| Frontend  | React 18, Vite, TypeScript, plain CSS                |
| Documents | PyMuPDF (PDF), python-docx (DOCX), vision/OCR, bs4   |
| Tests     | pytest (29 tests, no live model calls)               |

## Setup

```bash
cd ai-business-discovery

# Backend
python -m venv backend/.venv
backend/.venv/Scripts/activate        # Windows;  source backend/.venv/bin/activate on macOS/Linux
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

### Environment

```bash
cp .env.example backend/.env
```

```env
GEMINI_API_KEY=AIza...       # leave empty to run the offline mock agent
GEMINI_MODEL=gemini-2.5-flash
ALLOW_MOCK_LLM=true
DATABASE_URL=sqlite:///./app.db
```

Get a **free** key at <https://aistudio.google.com/apikey> — sign in with a Google
account, *Create API key*, paste it into `backend/.env`. No billing setup is needed
for the free tier. The key is read by the backend only and is never sent to the
browser.

Free-tier notes: `gemini-2.5-flash` serves both the structured discovery call and
screenshot vision. If you hit the rate limit the API returns `RESOURCE_EXHAUSTED` and
the UI shows the message verbatim — wait a minute, or set
`GEMINI_MODEL=gemini-2.5-flash-lite`, which has a higher free quota.

> **No API key?** The app still runs end to end. With no key configured the Discovery
> Agent falls back to a deterministic offline analyser that mines the real uploaded
> text, and every response is flagged `mocked: true` and says so in `assumptions`.
> Contracts, endpoints and UI are identical.

### Run

```bash
# Terminal 1 — backend  (from ai-business-discovery/backend)
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend (from ai-business-discovery/frontend)
npm run dev
```

Open http://localhost:5173. API docs are at http://localhost:8000/docs.
The Vite dev server proxies `/api` to the backend, so no CORS setup is needed.

With Docker: `docker compose up` (backend on 8000, frontend on 5173).

### Tests

```bash
cd backend && pytest -q      # 29 passed
```

Tests never call a real model — they run against the deterministic agent.

## Sample data

`sample_data/` contains a fictional facilities-management client (Northwind) whose
purchase-approval process runs on email, WhatsApp and a shared spreadsheet:

| File                  | Type               |
| --------------------- | ------------------ |
| `meeting-1.txt`       | Discovery call transcript |
| `meeting-2.txt`       | Follow-up call transcript |
| `whatsapp.txt`        | WhatsApp export    |
| `current-process.md`  | Procedure document (source for the PDF) |
| `current-process.pdf` | Same procedure as a PDF |
| `current-app.png`     | Screenshot of the spreadsheet in use today |

The PDF and PNG are generated (keeping binaries out of diffs):

```bash
python sample_data/generate_binary_samples.py
```

Screenshot ingestion needs either `GEMINI_API_KEY` (vision) or a local
`pytesseract` install; without either, the upload fails with a clear message and the
other input types carry on working.

## Demo flow

1. Create a project.
2. Upload `meeting-1.txt`, `whatsapp.txt`, `current-process.pdf` (and `current-app.png`
   if vision is configured). Each becomes `src-001`, `src-002`, … with a detected type.
3. Click **Analyze business** — one AI call over the canonical input.
4. **Discovery** tab: business need, reconstructed current process, pain points,
   requirements (labelled fact / inference / assumption), missing information,
   contradictions, recommended process. Every claim shows the source files behind it.
   *Show canonical input JSON* reveals the exact contract handed to the agent.
5. **Solution** tab: roles, modules, features, screens, workflow.
6. **POC** tab: fill the generated request form, walk the workflow as each role,
   approve or reject, and watch the status and audit trail update.

## API

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET    | `/api/health` | Status, AI mode, available extractors |
| POST   | `/api/projects` | Create a project |
| GET    | `/api/projects` · `/api/projects/{id}` | List / read |
| POST   | `/api/projects/{id}/reset` | Clear sources and analyses |
| POST   | `/api/projects/{id}/sources` | Upload a file |
| POST   | `/api/projects/{id}/sources/url` | Add a website |
| GET    | `/api/projects/{id}/sources` | List normalized sources |
| DELETE | `/api/projects/{id}/sources/{source_id}` | Remove a source |
| GET    | `/api/projects/{id}/canonical-input` | The exact AI input contract |
| POST   | `/api/projects/{id}/analyze` | Run the Discovery Agent |
| GET    | `/api/projects/{id}/discovery` | Latest stored analysis + POC blueprint |

## Design decisions

**Why one agent.** The problem is *collect → normalize → understand → structure →
demonstrate*. That is a pipeline, not a negotiation. Splitting it across agents would
add orchestration, latency, cost and disagreement between agents without improving any
answer. One prompt sees all the evidence at once, which is exactly what a consultant
needs to spot contradictions.

**Why no LangChain or LangGraph.** There is one stateless, structured call to one
model. LangChain earns its place when you need chains, tool loops, memory or retrieval
plumbing; LangGraph earns its place when you need a stateful multi-agent graph. This
system has none of those, so a framework would only add a dependency, a version
treadmill and a layer of indirection between `discovery_agent.py` and
`generate_content`. The provider SDK is called directly, from one file
(`services/llm_client.py`), which is also what makes swapping providers a one-file
change.

**Why canonical JSON first.** It decouples input formats from analysis. New format =
new adapter. It also makes the AI layer testable with fixtures, and it is what makes
source traceability possible at all.

**Why the AI does not generate UI.** The agent returns *what the application should
do*; `poc_service.py` turns that into a blueprint and React renders it with fixed
components. Deterministic, safe, reviewable, and it never breaks because a model
emitted invalid JSX.

**Grounding.** Pain points, requirements and process steps carry `source_ids`, and the
UI resolves them to file names. Inference is labelled, unknowns go to
`missing_information`, and disagreements go to `contradictions` instead of being
silently resolved.

**Validation.** Gemini enforces the `DiscoveryOutput` schema server-side via
`response_schema`, so the SDK returns an already-parsed Pydantic object; raw-text
parsing is the fallback, followed by one deterministic repair retry on schema failure.
Never a silent accept — and no second agent to validate the first.

**Persistence.** Both the canonical input and the discovery output are stored with the
model name and prompt version, so any analysis can be reproduced and audited.

## Deliberately out of scope

Direct Teams/WhatsApp integrations (exports are accepted instead), authentication,
multi-agent orchestration, vector databases and RAG (the whole normalized package fits
in one context for POC-sized inputs), background job queues, and production
infrastructure.

If input size ever exceeds the limit, the intended fallback is deterministic chunking
plus one consolidation call — not more agents. Today the backend refuses oversized
input with a clear message rather than silently truncating the analysis.
