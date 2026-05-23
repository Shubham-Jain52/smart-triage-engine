# Technical Requirement Document (TRD)

## 1. Technology Stack

### Phase 1 (Implemented)

| Layer | Technology |
|-------|------------|
| API | FastAPI (Python 3.10+) |
| Async jobs | FastAPI `BackgroundTasks` |
| Classification | Hugging Face zero-shot (`transformers`, `torch`) |
| Optional offline train | scikit-learn TF-IDF + Logistic Regression |
| HTTP client | `httpx` (outbound routing callback) |
| Container | Docker |

### Phase 2 — RAG (Planned)

| Layer | Technology |
|-------|------------|
| Vector DB | **Pinecone** (BYOK API key + index) |
| Embeddings | **Sentence-Transformers** (local embedding generation) |
| RAG orchestration | **LangChain** or **LlamaIndex** (retrieval + prompt assembly) |
| Diagram format | **Mermaid** (flowchart syntax in API + Jira comments) |
| LLM inference | **Ollama** (local default) or BYOK cloud API (OpenAI-compatible / Anthropic per config) |

### Phase 3–4 — Orchestration & Packaging (Planned)

| Layer | Technology |
|-------|------------|
| Workflow automation | **n8n** (local instance, Jira nodes + HTTP Request) |
| Ticketing UI | **Jira Cloud** (primary; triggers and write-back) |
| Multi-service deploy | **Docker Compose** (API + n8n + optional Ollama) |
| Configuration | Single root **`.env`** consumed by compose and API |

### Phase 5 — Historical Data Ingestion (Planned)

| Layer | Technology |
|-------|------------|
| Source system | **Jira REST API** (JQL search for resolved issues) |
| Embeddings | **Sentence-Transformers** (same model as Phase 2 retrieval) |
| Vector store | **Pinecone Python Client** (batch upsert) |
| Execution | Standalone CLI script **`ingest.py`** (not part of FastAPI process) |

## 2. API Specifications

### POST /api/v1/triage

Receives ticket data from n8n, Jira Automation, or a simulator.

**Request (JSON):**

| Field | Type | Required |
|-------|------|----------|
| `ticket_id` | string | yes |
| `title` | string | yes |
| `description` | string | yes |
| `created_at` | datetime (ISO 8601) | yes |

**Immediate response:** `202 Accepted`

```json
{
  "ticket_id": "PROJ-42",
  "status": "processing"
}
```

Processing runs asynchronously (classification + Phase 2 RAG when enabled).

### GET /api/v1/triage/{ticket_id}

Retrieves the full triage result when processing completes.

**Response (JSON) — Phase 1 fields:**

| Field | Type | Description |
|-------|------|-------------|
| `ticket_id` | string | Same as ingest id (e.g. Jira issue key) |
| `assigned_team` | string | Predicted team label |
| `confidence_score` | float | 0.0–1.0 |
| `requires_hitl` | boolean | `true` if confidence &lt; `HITL_THRESHOLD` |
| `status` | string | `processing` \| `completed` \| `failed` |

**Response — Phase 2 fields (planned, required when RAG enabled):**

| Field | Type | Agent-facing | Description |
|-------|------|----------------|-------------|
| `problem_flowchart_mermaid` | string | **Yes** | Mermaid `flowchart` for the **current** ticket (symptoms → checks → branches) |
| `resolution_flowchart_mermaid` | string | **Yes** | Mermaid `flowchart` summarizing **how similar past tickets were fixed** (merged from top-k retrieval) |
| `rag_resolution_summary` | string | Optional | Short caption above diagrams (1–2 sentences); not a substitute for flowcharts |
| `similar_past_tickets` | array of string | **No** (audit) | Top-k Pinecone ids for logs/support; **omit from default Jira comment** |

**Example completed response:**

```json
{
  "ticket_id": "PROJ-42",
  "assigned_team": "DevOps",
  "confidence_score": 0.91,
  "requires_hitl": false,
  "status": "completed",
  "rag_resolution_summary": "VPN-style connectivity issue; past fixes focused on cert and session state.",
  "problem_flowchart_mermaid": "flowchart TD\n  A[User reports VPN drop] --> B{Auth OK?}\n  B -->|No| C[Check cert expiry]\n  B -->|Yes| D[Check gateway sessions]",
  "resolution_flowchart_mermaid": "flowchart TD\n  P1[Past: VPN drops] --> P2[Renew client cert]\n  P2 --> P3[Clear stale sessions]\n  P3 --> P4[Verify stable 30m]",
  "similar_past_tickets": ["DEMO-101", "DEMO-111", "DEMO-106"]
}
```

When RAG is disabled or fails, diagram fields and summary are empty strings; `similar_past_tickets` is `[]`; routing fields remain populated if classification succeeded.

**Jira comment layout (Phase 3):** Post two fenced Mermaid blocks (problem, then past resolutions). Do not paste `similar_past_tickets` as the primary guidance for agents.

**Outbound callback:** If `TRIAGE_CALLBACK_URL` is set, the same JSON body (including Phase 2 fields) is POSTed to n8n or the ticketing platform when status becomes terminal.

### Authentication (optional)

* **Inbound:** `WEBHOOK_INGEST_API_KEY` → require `X-API-Key` on POST.
* **Outbound callback:** `TRIAGE_CALLBACK_API_KEY` → sent as `X-API-Key` on callback POST.

## 3. ML Model Strategy (Phase 1)

### 3.1 Implemented runtime

* **Classifier:** Hugging Face `zero-shot-classification` (`ZS_MODEL_NAME`, default `valhalla/distilbart-mnli-12-1`).
* **Labels:** `CANDIDATE_LABELS` (comma-separated env).
* **Preprocessor:** Concatenate title + description; lowercase; strip punctuation ([`preprocessor.py`](../src/models/preprocessor.py)).
* **HITL:** `requires_hitl` when confidence &lt; `HITL_THRESHOLD` (default `0.80`).

### 3.2 Optional offline alternative

* [`train.py`](../src/models/train.py) — TF-IDF + Logistic Regression pickles; not default runtime.

## 4. RAG Architecture Flow (Phase 2 — Implemented)

Executed inside the background triage worker **after** (or in parallel with) ML classification when `RAG_ENABLED=true`.

```text
1. Extract ticket text
   └── title + description (same preprocessor as classification)

2. Generate embedding locally
   └── Sentence-Transformers model (config: EMBEDDING_MODEL_NAME)

3. Query Pinecone (internal)
   └── index.query(vector, top_k=3, include_metadata)
   └── collect resolution_text + ticket_id per match (audit list only)

4. LLM — problem flowchart
   └── Prompt: current ticket only
   └── Output: problem_flowchart_mermaid (valid Mermaid flowchart TD/LR)

5. LLM — resolution flowchart
   └── Prompt: current ticket + top-k problem/resolution metadata (no requirement to label nodes with ticket ids)
   └── Output: resolution_flowchart_mermaid (merged “how we fixed similar issues” path)

6. Optional caption
   └── rag_resolution_summary (1–2 sentences)

7. Persist in cache + callback payload
   └── similar_past_tickets = [id1, id2, id3]  (API audit; not shown in default Jira UI)
   └── problem_flowchart_mermaid, resolution_flowchart_mermaid
```

### 4.1 Flowchart generation rules

| Diagram | Input | Intent |
|---------|--------|--------|
| **Problem** | Current title + description | Help assignee **structure** the incident (symptoms, decision points) |
| **Resolution** | Top-k `resolution_text` from Pinecone | Help assignee see a **proven fix path** abstracted from history |

* **Format:** Mermaid only in v1 (`flowchart TD` or `flowchart LR`); validate syntax before returning (retry or sanitize on parse failure).
* **No chunking** in Pinecone ingest; flowcharts are generated at **query time**, not stored as vectors.
* **Privacy:** Diagram generation uses the same local/BYOK LLM policy as summaries; no extra external calls beyond configured provider.

**Pinecone metadata (required for Phase 2 + populated by Phase 5):**

| Metadata key | Source | Purpose |
|--------------|--------|---------|
| `ticket_id` | Jira issue key | Vector id + `similar_past_tickets` references |
| `title` | Jira `summary` | Stored for LLM context |
| `description` | Jira `description` | Stored for audit / optional re-embed |
| `resolution_text` | Resolution comment or status notes | **Solution** text for RAG generation |
| `team` | Component / assignee group / custom field | Optional routing context |
| `resolved_at` | Jira resolution date | Filtering / freshness |

**Embedding input (Phase 5 ingest):** vector computed from **Title + Description** (after text cleaning). Resolution text is stored in metadata for retrieval prompts, not necessarily concatenated into the embedding (configurable; default: problem-only embedding for similarity search).

**Failure behavior:** Log error; return empty RAG fields; do not fail routing if classification succeeded unless configured otherwise.

## 5. Phase 5: Ingestion Pipeline (Cold Start — Planned)

Standalone, **one-time** (or occasional re-run) batch job. Runs **before** enabling `RAG_ENABLED` in production, and is **completely separate** from the live FastAPI web server.

### 5.1 APIs & tools

| Component | Role |
|-----------|------|
| **Jira REST API** | Search issues via **JQL**; fetch fields and comment history |
| **sentence-transformers** | Local embedding generation (no embedding API calls) |
| **Pinecone Python Client** | `upsert` vectors + metadata payloads |

### 5.2 Data pipeline steps

```text
1. Fetch tickets (Jira REST)
   └── JQL example: project = PROJ AND status = Resolved
                    AND resolved >= -12m
   └── Pagination until window exhausted

2. Extract knowledge per issue
   └── Problem: fields.summary + fields.description
   └── Solution: resolution comment (preferred) or resolution field / last internal comment

3. Clean text
   └── Strip HTML/ADF from Jira description where applicable
   └── Normalize whitespace; optional shared preprocessor with Phase 1

4. Generate embedding (local)
   └── Sentence-Transformers on (Title + Description)
   └── Model: EMBEDDING_MODEL_NAME (same as Phase 2)

5. Upsert to Pinecone
   └── Vector id = ticket_id (issue key)
   └── Metadata = { ticket_id, title, description, resolution_text, team, resolved_at }
   └── Namespace: PINECONE_NAMESPACE (optional)

6. Report
   └── Count upserted / skipped / failed; log failures per ticket_id
```

### 5.3 Execution model

| Attribute | Value |
|-----------|--------|
| Entry point | `ingest.py` (project root or `scripts/ingest.py`) |
| Invocation | `python ingest.py` or `PYTHONPATH=. python scripts/ingest.py` |
| Process | CLI batch job; **no HTTP server** |
| Config | Reads same `.env` as API (`PINECONE_*`, `JIRA_*`, `EMBEDDING_MODEL_NAME`, `INGEST_MONTHS=12`) |
| Idempotency | Upsert by `ticket_id`; safe to re-run after Jira backfill |

### 5.4 Relationship to other phases

```text
Phase 5 (ingest.py)  ──►  Pinecone index populated
                              │
Phase 2 (live RAG)   ◄──  query + LLM (requires non-empty index)
Phase 3 (n8n)        ◄──  uses Phase 2 output on new tickets
Phase 3.1 (on-resolve) ──►  incremental Pinecone upsert after each resolve
```

### 5.5 Phase 3.1 — On-Resolve Re-Ingest (Implemented)

Continuous ingest when Jira issues are resolved. Reuses Phase 5 pipeline (`upsert_tickets_to_pinecone`, same metadata schema). Does **not** ingest open tickets or live triage POSTs.

**Triggers:**

| Trigger | Entry point | When to use |
|---------|-------------|-------------|
| Webhook (primary) | `POST /api/v1/ingest/resolved` | Jira Automation on status → Resolved/Done/Closed |
| Poll (fallback) | `scripts/poll_resolved_ingest.py --once` | Cron when webhooks unavailable |

**API — POST `/api/v1/ingest/resolved`**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ticket_id` | string | Yes | Jira issue key (e.g. `PROJ-42`) |

**Response (200):**

```json
{
  "ticket_id": "PROJ-42",
  "status": "ingested",
  "message": "upserted 1 vector(s)"
}
```

`status`: `ingested` | `skipped` | `failed`. Auth: optional `X-API-Key` when `WEBHOOK_INGEST_API_KEY` is set.

**Skip rules:** non-resolved status; empty title+description; optional skip when `INGEST_ON_RESOLVE_REQUIRE_RESOLUTION=true` and no usable resolution text.

**Config:** `INGEST_ON_RESOLVE_ENABLED`, `INGEST_ON_RESOLVE_REQUIRE_RESOLUTION`, `INGEST_ON_RESOLVE_POLL_MINUTES`, `INGEST_ON_RESOLVE_POLL_INTERVAL_SECONDS`.

**Implementation:** [`src/services/resolve_ingest_service.py`](../src/services/resolve_ingest_service.py), [`scripts/poll_resolved_ingest.py`](../scripts/poll_resolved_ingest.py). Operator guide: [PHASE3_1_ON_RESOLVE_INGEST.md](PHASE3_1_ON_RESOLVE_INGEST.md).

## 6. n8n Workflow Requirements (Phase 3 — Planned)

Reference implementation lives under `integrations/n8n/`. Minimum node graph:

| Step | n8n node | Action |
|------|----------|--------|
| 1 | **Jira Trigger** | Issue Created (project/filter as configured) |
| 2 | **HTTP Request** | `POST` `{TRIAGE_API_URL}/api/v1/triage` with mapped `ticket_id`, `title`, `description`, `created_at` |
| 3 | **Wait / Loop** | Poll `GET /api/v1/triage/{ticket_id}` until `status` ≠ `processing` **or** separate workflow triggered by `TRIAGE_CALLBACK_URL` webhook |
| 4 | **Jira** — Update issue | Set assignee / component / labels from `assigned_team`; handle `requires_hitl` |
| 5 | **Jira** — Add comment | Internal comment: caption + **problem** Mermaid block + **past resolutions** Mermaid block (not a similar-ticket list) |

**Field mapping (Jira → POST body):**

| Triage field | Jira source |
|--------------|-------------|
| `ticket_id` | Issue key (`PROJ-42`) |
| `title` | `fields.summary` |
| `description` | `fields.description` |
| `created_at` | `fields.created` |

**Jira comment template (Python worker / Phase 3 example):**

```text
[Auto-Triage] Team: {{ assigned_team }} | Confidence: {{ confidence_score }} | HITL: {{ requires_hitl }}
{{ rag_resolution_summary }}

h3. Current problem (flowchart)
```mermaid
{{ problem_flowchart_mermaid }}
```

h3. How similar issues were resolved (flowchart)
```mermaid
{{ resolution_flowchart_mermaid }}
```
```

Audit ids (`similar_past_tickets`) may be logged server-side or appended in debug mode only (`INCLUDE_TICKET_IDS_IN_COMMENT=false` default).

See [INTEGRATION_N8N_JIRA.md](INTEGRATION_N8N_JIRA.md) for poll vs callback patterns.

## 7. Architectural Workflow (End-to-End)

### 7.1 One-time bootstrap (Phase 5)

```text
Operator runs ingest.py
    → Jira REST (JQL: resolved tickets, last 12 months)
    → Clean + embed (Title + Description)
    → Pinecone upsert (metadata includes resolution comment)
    → Index ready for Phase 2 retrieval
```

### 7.2 Live ticket flow (Phases 1–3)

```text
Jira (Issue Created)
    → n8n Jira Trigger
    → HTTP POST /api/v1/triage (202)
    → FastAPI BackgroundTasks
         ├─ Zero-shot classify → assigned_team, confidence, requires_hitl
         └─ RAG (Phase 2) → problem + resolution Mermaid flowcharts
    → GET result OR callback POST
    → Python Jira worker: Update assignee + Add comment with diagrams
```

## 8. Docker Compose Topology (Phase 4 — Planned)

| Service | Role | Ports (example) |
|---------|------|-----------------|
| `triage-api` | FastAPI + ML + RAG | 8000 |
| `n8n` | Workflow engine | 5678 |
| `ollama` | Local LLM (optional) | 11434 |

**Configuration:** All services read from shared `.env` (Pinecone, Jira URLs for n8n credentials, `CANDIDATE_LABELS`, `RAG_ENABLED`, etc.).

## 9. Target Project Structure

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the full proposed tree. Summary:

```text
ticket_routing_agent/
├── docker-compose.yml          # Phase 4: api + n8n + ollama
├── .env.example                # Single BYOK + service config
├── docs/
│   ├── PRD.md
│   ├── TRD.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── INTEGRATION_N8N_JIRA.md
│   └── HANDOFF_N8N_JIRA_PROMPT.md
├── integrations/
│   └── n8n/
│       ├── README.md
│       ├── workflow-jira-triage-poll.json
│       └── jira-team-mapping.example.json
├── scripts/
│   ├── evaluate_accuracy.py
│   ├── latency_sample.py
│   ├── ingest_historical_tickets.py   # Optional CSV seed (dev/demo)
│   └── ingest.py                      # Phase 5: Jira → Pinecone cold start (primary)
├── src/
│   ├── api/v1/
│   ├── models/
│   │   ├── ml_classifier.py
│   │   ├── preprocessor.py
│   │   └── embeddings.py              # Phase 2
│   ├── rag/                           # Phase 2
│   │   ├── pinecone_client.py
│   │   ├── retriever.py
│   │   ├── flowchart_generator.py       # problem + resolution Mermaid via LLM
│   │   └── resolution_generator.py      # optional caption / legacy summary
│   └── services/
│       ├── triage_service.py          # orchestrates classify + RAG
│       ├── rag_service.py             # Phase 2
│       └── ...
└── tests/
    ├── test_rag_service.py            # Phase 2
    └── ...
```

## 10. Implementation Status

| Area | Phase | Status |
|------|-------|--------|
| FastAPI ingest + GET + callback | 1 | **Implemented** |
| Zero-shot classification + HITL | 1 | **Implemented** |
| Idempotency + optional API key | 1 | **Implemented** |
| Unit / integration tests (core API) | 1 | **Implemented** |
| Dockerfile | 1/4 | **Implemented** (compose expansion planned) |
| RAG: embeddings + Pinecone query | 2 | **Implemented** ([`src/rag/retriever.py`](../src/rag/retriever.py)) |
| RAG: problem + resolution Mermaid flowcharts | 2 | **Implemented** ([`src/rag/flowchart_generator.py`](../src/rag/flowchart_generator.py)) |
| RAG: LLM client (Ollama / OpenAI) | 2 | **Implemented** ([`src/integrations/llm/client.py`](../src/integrations/llm/client.py)) |
| RAG: `rag_service` orchestration | 2 | **Implemented** ([`src/services/rag_service.py`](../src/services/rag_service.py)) |
| API schema: `problem_flowchart_mermaid`, `resolution_flowchart_mermaid`, audit `similar_past_tickets` | 2 | **Implemented** |
| n8n workflow exports + Jira write-back | 3 | Optional (Python worker is primary) |
| Python Jira worker (`worker.py`, `run_jira_worker.py`) | 3 | **Implemented** |
| Jira comment formatter (Mermaid ADF) | 3 | **Implemented** |
| Team mapping JSON | 3 | **Implemented** |
| On-resolve Pinecone re-ingest (webhook + poll) | 3.1 | **Implemented** ([`src/services/resolve_ingest_service.py`](../src/services/resolve_ingest_service.py)) |
| `POST /api/v1/ingest/resolved` | 3.1 | **Implemented** |
| Poll script `poll_resolved_ingest.py` | 3.1 | **Implemented** |
| docker-compose (api + n8n + ollama) | 4 | Planned |
| Single `.env` for full stack | 4 | Planned |
| **`ingest.py` Jira → Pinecone cold start** | 5 | **Implemented** ([`scripts/ingest.py`](../scripts/ingest.py)) |
| Jira JQL fetch + resolution comment extraction | 5 | **Implemented** ([`src/integrations/jira/`](../src/integrations/jira/)) |
| Batch upsert with full metadata | 5 | **Implemented** ([`src/rag/pinecone_client.py`](../src/rag/pinecone_client.py)) |
| Index setup script | 5 | **Implemented** ([`scripts/setup_pinecone_index.py`](../scripts/setup_pinecone_index.py)) |
| Smoke query script | 5 | **Implemented** ([`scripts/pinecone_smoke_query.py`](../scripts/pinecone_smoke_query.py)) |
| CSV seed script (`ingest_historical_tickets.py`) | 2/5 | Planned (dev fallback) |

## 11. Environment Variables (Planned additions)

| Variable | Phase | Purpose |
|----------|-------|---------|
| `RAG_ENABLED` | 2 | Toggle RAG pipeline |
| `PINECONE_API_KEY` | 2 | BYOK vector DB |
| `PINECONE_INDEX_NAME` | 2 | Target index |
| `PINECONE_NAMESPACE` | 2 | Optional namespace |
| `EMBEDDING_MODEL_NAME` | 2 | Sentence-Transformers model id |
| `RAG_TOP_K` | 2 | Default `3` |
| `OLLAMA_BASE_URL` | 2 | Local LLM base URL |
| `OLLAMA_MODEL` | 2 | Model tag for resolution generation |
| `LLM_PROVIDER` | 2 | `ollama` \| `openai` \| … |
| `FLOWCHART_MAX_NODES` | 2 | Cap diagram size (default e.g. 15) |
| `INCLUDE_TICKET_IDS_IN_COMMENT` | 3 | Default `false` — hide `similar_past_tickets` from Jira |
| `TRIAGE_API_URL` | 3/4 | Base URL for Python worker → triage API |
| `JIRA_BASE_URL` | 5 | e.g. `https://<site>.atlassian.net` |
| `JIRA_EMAIL` | 5 | API token owner email (Cloud) |
| `JIRA_API_TOKEN` | 5 | BYOK Jira credential |
| `JIRA_PROJECT_KEY` | 5 | Scope ingest to one project |
| `INGEST_JQL` | 5 | Override default resolved-ticket query |
| `INGEST_MONTHS` | 5 | Lookback window (default `12`) |
| `INGEST_BATCH_SIZE` | 5 | Pinecone upsert batch size |
| `INGEST_ON_RESOLVE_ENABLED` | 3.1 | Master switch for on-resolve ingest |
| `INGEST_ON_RESOLVE_REQUIRE_RESOLUTION` | 3.1 | Skip when no usable resolution text |
| `INGEST_ON_RESOLVE_POLL_MINUTES` | 3.1 | Poll script JQL lookback |
| `INGEST_ON_RESOLVE_POLL_INTERVAL_SECONDS` | 3.1 | Poll daemon interval |

Existing Phase 1 variables remain documented in [`.env.example`](../.env.example).

**Recommended run order:** Phase 5 `ingest.py` → enable `RAG_ENABLED` (Phase 2) → Phase 3 n8n live workflow → Phase 4 compose for packaging.
