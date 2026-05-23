# Implementation Plan — Phase 2 (RAG) & Phase 4 (Docker / n8n Packaging)

Phase 1 (ML triage API) is **complete and tested**. This checklist covers what to build next. Phase 3 (n8n workflow JSON) can proceed in parallel once API response fields exist.

---

## Proposed directory structure (target)

```text
ticket_routing_agent/
├── .env                          # Single config (gitignored); copy from .env.example
├── .env.example                  # All phases: API, RAG, Pinecone, Ollama, n8n, Jira hints
├── .python-version
├── docker-compose.yml            # triage-api, n8n, ollama (optional)
├── Dockerfile                    # triage-api image
├── requirements.txt              # + sentence-transformers, pinecone-client, langchain|llamaindex
├── README.md
│
├── docs/
│   ├── PRD.md
│   ├── TRD.md
│   ├── IMPLEMENTATION_PLAN.md    # this file
│   ├── INTEGRATION_N8N_JIRA.md
│   └── HANDOFF_N8N_JIRA_PROMPT.md
│
├── integrations/
│   └── n8n/
│       ├── README.md
│       ├── workflow-jira-triage-poll.json
│       ├── workflow-jira-triage-callback.json   # optional
│       └── jira-team-mapping.example.json
│
├── scripts/
│   ├── evaluate_accuracy.py
│   ├── latency_sample.py
│   └── ingest_historical_tickets.py             # CSV/JSON → Pinecone upsert
│
├── src/
│   ├── main.py
│   ├── config.py                                # + RAG, Pinecone, Ollama settings
│   ├── api/
│   │   └── v1/
│   │       ├── routes.py
│   │       ├── schemas.py                       # + rag_resolution_summary, similar_past_tickets
│   │       └── deps.py
│   ├── models/
│   │   ├── ml_classifier.py
│   │   ├── preprocessor.py
│   │   ├── embeddings.py                        # Sentence-Transformers wrapper
│   │   └── train.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── pinecone_client.py                   # connect, query, upsert helpers
│   │   ├── retriever.py                         # embed + top_k query
│   │   └── resolution_generator.py              # LangChain/LlamaIndex + Ollama/BYOK LLM
│   ├── services/
│   │   ├── triage_service.py                    # wire classify + rag_service
│   │   ├── rag_service.py                       # orchestrate retriever + generator
│   │   ├── cache_service.py
│   │   └── callback_service.py
│   └── data/
│       ├── validation_set.csv
│       └── historical_tickets.example.csv       # seed format for Pinecone ingest
│
└── tests/
    ├── conftest.py
    ├── test_api.py                              # assert RAG fields on GET
    ├── test_rag_service.py                      # mock Pinecone + LLM
    ├── test_embeddings.py
    ├── test_callback_service.py
    ├── test_ml_model.py
    └── test_services.py
```

---

## Phase 2 — RAG Resolution Engine

### 2.1 Configuration & dependencies

- [x] Add to `requirements.txt`: `sentence-transformers`, `pinecone-client`, `httpx`.
- [x] Extend `src/config.py` and `.env.example`: `RAG_ENABLED`, `PINECONE_*`, `EMBEDDING_MODEL_NAME`, `RAG_TOP_K`, `OLLAMA_*`, `LLM_PROVIDER`, `FLOWCHART_MAX_NODES`, optional OpenAI keys.
- [x] Document BYOK: no secrets in Docker image; keys only via `.env`.

### 2.2 Embeddings module

- [x] `src/models/embeddings.py` — embed / embed_batch / embedding_dimension.

### 2.3 Pinecone integration

- [x] `src/rag/pinecone_client.py` — upsert, query, ensure_serverless_index.
- [x] Phase 5 ingest: `scripts/ingest.py` + `src/data/historical_tickets.csv` (dummy/Jira sources).
- [x] Metadata schema for flowchart prompts: `title`, `description`, `resolution_text`, `team`, `resolved_at` ([`src/rag/retriever.py`](../src/rag/retriever.py) `METADATA_KEYS`).

### 2.4 Retrieval & flowchart generation

- [x] Create `src/rag/retriever.py`: embed ticket → Pinecone top_k → audit ids + context blobs.
- [x] Create `src/rag/flowchart_generator.py`: problem + resolution Mermaid via BYOK LLM.
- [x] Create `src/rag/resolution_generator.py`: short `rag_resolution_summary` caption.
- [x] Create `src/integrations/llm/client.py`: Ollama + OpenAI-compatible chat.

### 2.5 Service orchestration

- [x] Create `src/services/rag_service.py`: `run_rag(...) -> RagResult`.
- [x] Update `src/services/triage_service.py`: after classify, if `RAG_ENABLED`, call `rag_service`.
- [x] On RAG failure: log warning; empty diagram fields; keep routing result.

### 2.6 API schema & callback

- [x] Update `src/api/v1/schemas.py` `TicketStatusResponse` with RAG fields.
- [x] Ensure `callback_service` serializes all fields via `model_dump`.
- [x] Update `tests/test_api.py`: stub `rag_service` returning sample Mermaid strings.

### 2.7 Tests & validation

- [x] `tests/test_rag_service.py`, `tests/test_flowchart_generator.py`, `tests/test_retriever.py`, `tests/test_llm_client.py`.
- [x] `tests/test_embeddings.py` dimension sanity check.
- [ ] Manual: seed Pinecone → POST triage → GET returns two non-empty Mermaid blocks; render in GitHub/Jira preview (requires live Ollama + Pinecone).

---

## Phase 3 — Python Jira worker (orchestration)

Can start after Phase 2 diagram fields exist on GET/callback.

- [ ] `src/integrations/jira/worker.py` (or `scripts/run_jira_worker.py`): poll/webhook → POST triage → GET result.
- [ ] `src/integrations/jira/comment_formatter.py`: build Jira comment from caption + two fenced Mermaid blocks (see [TRD §6](TRD.md)).
- [ ] `jira-team-mapping.example.json` for `assigned_team` → assignee/component; respect `requires_hitl`.
- [ ] Env: `INCLUDE_TICKET_IDS_IN_COMMENT=false` by default.
- [ ] End-to-end test: issue created → comment shows **problem** and **resolution** flowcharts (not a similar-ticket bullet list).

**Deferred / optional:** n8n workflow exports under `integrations/n8n/` if a team prefers no-code ops later.

---

## Phase 3.1 — On-Resolve Re-Ingest

Independent of Phase 3 create-worker; can ship once Jira + Pinecone are configured.

- [x] Extend [`src/integrations/jira/client.py`](../src/integrations/jira/client.py): `get_issue`, `fetch_recently_resolved`, `RESOLVED_STATUSES`.
- [x] [`src/services/resolve_ingest_service.py`](../src/services/resolve_ingest_service.py): fetch → validate → `upsert_tickets_to_pinecone`.
- [x] `POST /api/v1/ingest/resolved` in [`src/api/v1/routes.py`](../src/api/v1/routes.py) + schemas.
- [x] [`scripts/poll_resolved_ingest.py`](../scripts/poll_resolved_ingest.py): `--once`, `--dry-run`, daemon loop.
- [x] Config: `INGEST_ON_RESOLVE_*` in [`src/config.py`](../src/config.py) and [`.env.example`](../.env.example).
- [x] Tests: `tests/test_resolve_ingest_service.py`, `tests/test_jira_client.py`, API tests.
- [x] Docs: [PHASE3_1_ON_RESOLVE_INGEST.md](PHASE3_1_ON_RESOLVE_INGEST.md).

---

## Phase 4 — Docker Compose packaging

### 4.1 Compose file

- [ ] Rewrite/extend `docker-compose.yml` services:
  - `triage-api` (build `Dockerfile`, port 8000, env_file `.env`, depends_on ollama if used).
  - `n8n` (official image, port 5678, volume for workflows, env_file `.env`).
  - `ollama` (optional profile `llm-local`, port 11434).
- [ ] Healthchecks: `GET /health` for API; n8n `/healthz` if available.

### 4.2 Single `.env`

- [ ] Consolidate `.env.example` sections: **API**, **ML**, **RAG**, **Pinecone**, **Ollama**, **n8n**, **Jira** (documentation comments only for Jira—credentials stored in n8n UI).
- [ ] `TRIAGE_API_URL=http://triage-api:8000` for n8n HTTP nodes inside compose network.

### 4.3 Dockerfile

- [ ] Multi-stage or slim image; optional model cache volume for HF + sentence-transformers.
- [ ] Document first-start download time in README.

### 4.4 Developer experience

- [ ] README section: `docker-compose up --build` quickstart.
- [ ] Verify `pytest` still runs on host; optional `docker compose run triage-api pytest`.

---

## Suggested implementation order

1. **Schemas + config** (RAG fields, env vars) — unblocks n8n template design.
2. **Embeddings + Pinecone client + ingest script** — need data before retrieval works.
3. **Retriever + Ollama generator + rag_service** — wire into triage_service.
4. **Tests** — mock external services.
5. **n8n workflows** — Jira comment with RAG output.
6. **docker-compose** — tie services together.

---

## Phase 1 reference (done)

| Item | Location |
|------|----------|
| POST/GET triage | `src/api/v1/routes.py` |
| Callback | `src/services/callback_service.py` |
| Classifier | `src/models/ml_classifier.py` |
| Tests | `tests/` (14 passing) |

No Phase 1 rework required unless RAG latency forces async split of classification vs RAG into separate background steps.
