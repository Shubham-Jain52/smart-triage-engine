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
| LLM inference | **Ollama** (local default) or BYOK cloud API (OpenAI-compatible / Anthropic per config) |

### Phase 3–4 — Orchestration & Packaging (Planned)

| Layer | Technology |
|-------|------------|
| Workflow automation | **n8n** (local instance, Jira nodes + HTTP Request) |
| Ticketing UI | **Jira Cloud** (primary; triggers and write-back) |
| Multi-service deploy | **Docker Compose** (API + n8n + optional Ollama) |
| Configuration | Single root **`.env`** consumed by compose and API |

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

| Field | Type | Description |
|-------|------|-------------|
| `rag_resolution_summary` | string | 2–3 sentence LLM-generated resolution strategy from retrieved context |
| `similar_past_tickets` | array of string | Top-k historical ticket IDs from Pinecone (e.g. `["IT-101", "IT-88", "IT-55"]`) |

**Example completed response:**

```json
{
  "ticket_id": "PROJ-42",
  "assigned_team": "DevOps",
  "confidence_score": 0.91,
  "requires_hitl": false,
  "status": "completed",
  "rag_resolution_summary": "Similar VPN dropouts were resolved by renewing the client certificate and clearing stale sessions on the gateway. Check user cert expiry and gateway session table before escalating.",
  "similar_past_tickets": ["IT-1042", "IT-987", "IT-801"]
}
```

When RAG is disabled or fails, `rag_resolution_summary` may be empty and `similar_past_tickets` an empty array; routing fields remain populated if classification succeeded.

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

## 4. RAG Architecture Flow (Phase 2 — Planned)

Executed inside the background triage worker **after** (or in parallel with) ML classification when `RAG_ENABLED=true`.

```text
1. Extract ticket text
   └── title + description (same preprocessor as classification)

2. Generate embedding locally
   └── Sentence-Transformers model (config: EMBEDDING_MODEL_NAME)

3. Query Pinecone
   └── index.query(vector, top_k=3, include_metadata)
   └── collect historical ticket_ids + resolution snippets from metadata

4. LLM synthesis
   └── Build prompt: current ticket + top-3 past contexts
   └── Ollama (OLLAMA_BASE_URL, OLLAMA_MODEL) or BYOK LLM API
   └── Output: rag_resolution_summary (2–3 sentences)

5. Persist in cache + callback payload
   └── similar_past_tickets = [id1, id2, id3]
   └── rag_resolution_summary = string
```

**Pinecone metadata (recommended):** `ticket_id`, `title`, `resolution_text`, `team`, `resolved_at`.

**Failure behavior:** Log error; return empty RAG fields; do not fail routing if classification succeeded unless configured otherwise.

## 5. n8n Workflow Requirements (Phase 3 — Planned)

Reference implementation lives under `integrations/n8n/`. Minimum node graph:

| Step | n8n node | Action |
|------|----------|--------|
| 1 | **Jira Trigger** | Issue Created (project/filter as configured) |
| 2 | **HTTP Request** | `POST` `{TRIAGE_API_URL}/api/v1/triage` with mapped `ticket_id`, `title`, `description`, `created_at` |
| 3 | **Wait / Loop** | Poll `GET /api/v1/triage/{ticket_id}` until `status` ≠ `processing` **or** separate workflow triggered by `TRIAGE_CALLBACK_URL` webhook |
| 4 | **Jira** — Update issue | Set assignee / component / labels from `assigned_team`; handle `requires_hitl` |
| 5 | **Jira** — Add comment | Internal comment body = `rag_resolution_summary` + optional list of `similar_past_tickets` |

**Field mapping (Jira → POST body):**

| Triage field | Jira source |
|--------------|-------------|
| `ticket_id` | Issue key (`PROJ-42`) |
| `title` | `fields.summary` |
| `description` | `fields.description` |
| `created_at` | `fields.created` |

**Comment template (example):**

```text
[Auto-Triage] Suggested resolution:
{{ $json.rag_resolution_summary }}

Similar past tickets: {{ $json.similar_past_tickets.join(', ') }}
Routed to: {{ $json.assigned_team }} (confidence: {{ $json.confidence_score }})
HITL required: {{ $json.requires_hitl }}
```

See [INTEGRATION_N8N_JIRA.md](INTEGRATION_N8N_JIRA.md) for poll vs callback patterns.

## 6. Architectural Workflow (End-to-End)

```text
Jira (Issue Created)
    → n8n Jira Trigger
    → HTTP POST /api/v1/triage (202)
    → FastAPI BackgroundTasks
         ├─ Zero-shot classify → assigned_team, confidence, requires_hitl
         └─ RAG pipeline → similar_past_tickets, rag_resolution_summary
    → GET result OR callback POST to n8n webhook
    → n8n Jira: Update assignee + Add internal comment
```

## 7. Docker Compose Topology (Phase 4 — Planned)

| Service | Role | Ports (example) |
|---------|------|-----------------|
| `triage-api` | FastAPI + ML + RAG | 8000 |
| `n8n` | Workflow engine | 5678 |
| `ollama` | Local LLM (optional) | 11434 |

**Configuration:** All services read from shared `.env` (Pinecone, Jira URLs for n8n credentials, `CANDIDATE_LABELS`, `RAG_ENABLED`, etc.).

## 8. Target Project Structure

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
│   └── ingest_historical_tickets.py   # Phase 2: Pinecone seeding
├── src/
│   ├── api/v1/
│   ├── models/
│   │   ├── ml_classifier.py
│   │   ├── preprocessor.py
│   │   └── embeddings.py              # Phase 2
│   ├── rag/                           # Phase 2
│   │   ├── pinecone_client.py
│   │   ├── retriever.py
│   │   └── resolution_generator.py
│   └── services/
│       ├── triage_service.py          # orchestrates classify + RAG
│       ├── rag_service.py             # Phase 2
│       └── ...
└── tests/
    ├── test_rag_service.py            # Phase 2
    └── ...
```

## 9. Implementation Status

| Area | Phase | Status |
|------|-------|--------|
| FastAPI ingest + GET + callback | 1 | **Implemented** |
| Zero-shot classification + HITL | 1 | **Implemented** |
| Idempotency + optional API key | 1 | **Implemented** |
| Unit / integration tests (core API) | 1 | **Implemented** |
| Dockerfile | 1/4 | **Implemented** (compose expansion planned) |
| RAG: embeddings + Pinecone query | 2 | Planned |
| RAG: LLM resolution summary | 2 | Planned |
| API schema: `rag_resolution_summary`, `similar_past_tickets` | 2 | Planned |
| Historical ingest script → Pinecone | 2 | Planned |
| n8n workflow exports + Jira write-back | 3 | Planned |
| docker-compose (api + n8n + ollama) | 4 | Planned |
| Single `.env` for full stack | 4 | Planned |

## 10. Environment Variables (Planned additions)

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
| `N8N_HOST`, `TRIAGE_API_URL` | 4 | Compose service URLs |

Existing Phase 1 variables remain documented in [`.env.example`](../.env.example).
