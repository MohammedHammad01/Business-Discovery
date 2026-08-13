# Architecture

## 1. Layers

```text
frontend/                    React 18 + Vite + TypeScript
  services/api.ts            typed fetch wrapper, one place for HTTP errors
  pages/                     Workspace · Analysis · Solution · POC
  components/primitives.tsx  Card, Badge, SourceRefs, Bullets, Spinner, Banner
  types/discovery.ts         mirrors the backend Pydantic contracts

backend/app/
  api/routes.py              HTTP boundary only: parse, delegate, map errors
  schemas/                   canonical.py · discovery.py · poc.py · api.py
  services/
    ingestion/               deterministic adapters + registry
    normalization/           text classification and cleanup
    llm_client.py            the only module that imports `google.genai`
    prompts.py               versioned system prompt (PROMPT_VERSION)
    discovery_agent.py       THE agent: CanonicalInput -> DiscoveryOutput
    mock_discovery.py        offline deterministic stand-in
    poc_service.py           DiscoveryOutput -> PocBlueprint (no AI)
    project_service.py       orchestration + persistence
  models/entities.py         projects · sources · analyses
  db/session.py              SQLAlchemy engine/session
```

## 2. Request flow

### Adding a source

```text
POST /api/projects/{id}/sources
   → size check (max_upload_bytes)
   → registry.select_adapter(filename, content_type)
   → adapter.extract()            deterministic; returns NormalizedSource
   → truncate to max_source_chars (flagged in metadata)
   → persist with ordinal → source_id "src-00N"
   → SourceRead
```

Adapter selection is ordered: PDF → DOCX → image → text. The text adapter is last
because it also claims any `text/*` content type. Type detection for `.txt` is a
regex classifier (`normalization/classifier.py`), not an AI call: WhatsApp exports
match a timestamped `dd/mm/yyyy, hh:mm - Name:` line shape; transcripts match speaker
or `[hh:mm:ss] Name:` lines.

### Analyzing

```text
POST /api/projects/{id}/analyze
   → build CanonicalInput from stored sources   (stable src-00N ids)
   → size check (max_total_content_chars)
   → BusinessDiscoveryAgent.run()
        ├─ no API key + mock allowed  → mock_discovery.build()
        └─ otherwise                  → one structured Gemini call
              ├─ response_schema=DiscoveryOutput  → response.parsed (server-enforced)
              ├─ fallback: response.text → json.loads → Pydantic validation
              └─ on ValidationError: ONE repair retry at temperature 0
   → persist canonical_input_json + discovery_output_json + model + prompt_version
   → poc_service.build_blueprint()   deterministic
   → AnalysisRead
```

## 3. Contracts

| Contract | Owner | Consumers |
| -------- | ----- | --------- |
| `CanonicalInput` | ingestion + service layer | the agent, the demo's "show canonical JSON" view |
| `DiscoveryOutput` | the agent | frontend rendering, `poc_service` |
| `PocBlueprint` | `poc_service` | the POC page only |

`CanonicalInput` is the stable contract. Adding an input format touches only an
adapter and the `SourceType` enum. Changing `DiscoveryOutput` requires touching the
prompt, the Pydantic model and `types/discovery.ts` together.

## 4. Traceability

Sources get human-readable ids (`src-001`) rather than UUIDs specifically so the model
can cite them cheaply and reliably. Pain points, requirements, process steps,
contradictions and the business need all carry `source_ids`; the frontend resolves
them to file names via a lookup built from the source list (`SourceRefs`). A claim
with no citation renders as "No source cited" rather than looking equally grounded.

Uncertainty is expressed in three separate places rather than being blended into the
prose:

* `requirements[].confidence` — `fact` / `inference` / `assumption`
* `assumptions[]` — what the proposal needs but the client never said
* `missing_information[]` — the questions to take back to the client
* `contradictions[]` — where two sources disagree

## 5. Error handling

| Failure | Handling |
| ------- | -------- |
| Unsupported file type | 400 listing supported extensions |
| Empty file / no extractable text | 400 with the specific reason |
| Extractor not installed | 501 naming the package to install |
| Malformed or private-network URL | 400 (SSRF guard: http/https only, no private/loopback/link-local) |
| Site unreachable / non-200 | 400 with the upstream status |
| Oversized upload or total input | 400 / 422 with the actual and allowed size |
| No API key | mock agent, or 422 if `ALLOW_MOCK_LLM=false` |
| AI timeout or transport error | 422 with the provider message |
| Schema-invalid AI JSON | one deterministic repair retry, then 422 |

`/api/health` reports which extractors are actually available in the running
environment, and the UI warns about the missing ones instead of failing mysteriously
at upload time.

## 6. Persistence

```text
projects (id, name, client_name, description, created_at)
sources  (id, project_id, ordinal, type, name, content, metadata_json, created_at)
analyses (id, project_id, canonical_input_json, discovery_output_json,
          model, prompt_version, mocked, created_at)
```

Analyses are append-only: re-running the analysis adds a row, and
`GET /discovery` returns the newest. Storing both sides of the AI call with the model
and prompt version is what makes an analysis reproducible after the fact.

## 7. Cost and latency

One AI call per analysis — not one per file, per section, or per stage. For the sample
data (~7,500 characters across four sources) a single `gemini-2.5-flash` call returns the
full discovery in a few seconds. Screenshot ingestion adds one vision call per image,
at upload time rather than analysis time.

If the input ever exceeds `max_total_content_chars`, the analysis is refused with a
clear message. The intended growth path is deterministic chunking plus one
consolidation call — not additional agents.

## 8. Testing

* **Unit** — adapter selection, WhatsApp/transcript classification, WhatsApp cleanup,
  truncation, SSRF rejection, POC blueprint derivation (including the fallback when
  the model returns no workflow).
* **Contract** — malformed AI JSON is rejected, fenced JSON is still parsed, discovery
  output validates, citations only reference real source ids.
* **API** — full flow (create → upload two types → canonical input → analyze →
  re-read), plus 400/404/422 paths, reset and delete.

All 29 tests run against the deterministic agent, so the suite is offline, free and
stable.
