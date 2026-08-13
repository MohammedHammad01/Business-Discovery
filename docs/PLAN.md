# PLAN.md — AI Business Discovery to POC

## 1. Objective

A one-week POC that converts scattered client information into a structured business
understanding and a practical application proposal. At least three input types must
work end to end.

## 2. Main design decision

**One AI agent + deterministic application services.**

```text
Input files / URL → deterministic ingestion → Canonical Input JSON
                  → ONE Business Discovery Agent → Discovery Output JSON
                  → deterministic POC UI
```

Multiple agents would add complexity without adding business value here. The problem
is `collect → normalize → understand → structure → demonstrate`; it does not require
agent-to-agent collaboration.

## 3. Functional flow

1. **Create project** — name, optional client name and description.
2. **Add inputs** — TXT/transcript, WhatsApp export, PDF, DOCX, screenshot, website URL.
3. **Normalize** — every source becomes `{source_id, type, name, content, metadata}`.
4. **Analyze** — one structured LLM call over the assembled `CanonicalInput`.
5. **Render** — discovery, solution and an interactive POC, all from validated JSON.

## 4. Delivery order

| Stage | Work | Status |
| ----- | ---- | ------ |
| 1 | Canonical + discovery schemas, FastAPI/React skeletons, sample data | done |
| 2 | Ingestion adapters: TXT, WhatsApp, transcript, PDF, DOCX, image, URL | done |
| 3 | Discovery Agent, versioned prompt, structured output, validation, repair retry | done |
| 4 | Frontend: upload workspace, source list, discovery cards, traceability badges | done |
| 5 | Deterministic POC blueprint + interactive happy path | done |
| 6 | Error handling, empty/loading states, persistence, health capabilities, tests | done |
| 7 | README, architecture doc, demo script | done |

## 5. Schemas

`CanonicalInput` (`backend/app/schemas/canonical.py`) and `DiscoveryOutput`
(`backend/app/schemas/discovery.py`). Both are Pydantic v2 and both are validated —
canonical input before the AI call, discovery output after it.

`DiscoveryOutput` deviates from the original sketch in one way: `business_need`,
`current_process` and `recommended_process` are concrete models instead of free-form
`dict`s, because strict JSON-schema enforcement needs defined properties and the
frontend needs to render them without null checks.

## 6. Handling uncertainty

Facts, inferences and assumptions are kept apart:

* `requirements[].confidence` labels each requirement `fact` / `inference` / `assumption`
* `assumptions[]` holds what the proposal needs but nobody said
* `missing_information[]` holds the questions for the client, each with a reason
* `contradictions[]` records where two sources disagree instead of silently picking one

## 7. Validation strategy

```text
CanonicalInput.model_validate  →  one structured LLM call  →  DiscoveryOutput.model_validate
                                                                    │ invalid
                                                                    ▼
                                                        one deterministic repair retry
                                                                    │ still invalid
                                                                    ▼
                                                                  422
```

No "validation agent" — validation is a Pydantic call.

## 8. AI cost / latency strategy

One AI call per analysis. Not one per file, per section or per stage. Sample inputs
are deliberately small enough for the one-call path. If input exceeds the configured
limit the analysis is refused with a clear message; the growth path is deterministic
chunking plus one consolidation call.

## 9. Testing

* Unit — adapters, classification, normalization, truncation, URL safety, POC blueprint
* Contract — schema validation, malformed/fenced AI JSON, citation integrity
* API — full happy path plus 400/404/422, reset, delete

A deterministic agent stands in for the model, so no automated test calls a provider.

## 10. Security

`.env` for secrets, never committed; the key stays server-side; upload size limits;
file-type allowlist; URL fetching restricted to http/https with private, loopback and
link-local addresses refused. Production-grade authentication is deliberately out of
scope for a POC.

## 11. Demo scenario

Northwind Facilities: purchase approvals run on email, WhatsApp and a shared
spreadsheet. Approvals sit unseen in an inbox, status in the spreadsheet goes stale,
rejection reasons are lost, and audit evidence takes a day to assemble.

Expected analysis: centralize and speed up approvals · pain points around manual
follow-up, invisible status and lost decisions · improvements around structured
requests, automatic routing, a decision queue, notifications and an audit trail ·
POC: create request → review → approve/reject → status.

If different sample data describes another process, the same pipeline applies — nothing
in the code is specific to approvals.

## 12. Demo script (5–8 minutes)

| Time | Beat |
| ---- | ---- |
| 0:00–0:45 | The problem: requirements arrive across channels and formats |
| 0:45–1:30 | Architecture: canonical JSON first, then one agent |
| 1:30–2:30 | Upload transcript, WhatsApp export, PDF, screenshot; show the source list |
| 2:30–3:00 | Show the canonical input JSON — the contract the AI actually sees |
| 3:00–4:15 | Analyze: business need, current process, pain points, requirements, gaps, improvements — with evidence badges |
| 4:15–5:00 | Solution: roles, modules, features, screens, workflow |
| 5:00–6:00 | POC: submit a request, approve it, watch status and audit trail |
| 6:00–7:00 | Engineering: FastAPI, Pydantic contracts, structured output, validation + repair, SQLite persistence, tests |
| 7:00–7:30 | Tradeoffs: no Teams/WhatsApp integration, no auth, no multi-agent orchestration, no RAG |

Closing line:

> "I optimized for reliability and delivery speed by converting every source into one
> canonical JSON contract and using a single Business Discovery Agent to reason over
> that normalized context. The POC is then rendered deterministically from validated
> structured output."
