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

- [ ] Add to `requirements.txt`: `sentence-transformers`, `pinecone-client` (or official SDK), `langchain` or `llamaindex`, `httpx` (already present).
- [ ] Extend `src/config.py` and `.env.example`: `RAG_ENABLED`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `PINECONE_NAMESPACE`, `EMBEDDING_MODEL_NAME`, `RAG_TOP_K`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `LLM_PROVIDER`, optional cloud LLM keys.
- [ ] Document BYOK: no secrets in Docker image; keys only via `.env`.

### 2.2 Embeddings module

- [ ] Create `src/models/embeddings.py`: load Sentence-Transformers model once (lazy singleton).
- [ ] Method `embed(text: str) -> list[float]` with batching optional for ingest script.

### 2.3 Pinecone integration

- [ ] Create `src/rag/pinecone_client.py`: init client from env; `query(vector, top_k)`; `upsert(records)`.
- [ ] Define metadata schema: `ticket_id`, `title`, `resolution_text`, `team`, `resolved_at`.
- [ ] Create `scripts/ingest_historical_tickets.py`: read CSV → embed → upsert (idempotent by `ticket_id`).
- [ ] Add `src/data/historical_tickets.example.csv` with 5–10 sample rows.

### 2.4 Retrieval & generation

- [ ] Create `src/rag/retriever.py`: embed ticket → Pinecone top_k → return `similar_past_tickets` + context strings.
- [ ] Create `src/rag/resolution_generator.py`: prompt template with current ticket + 3 contexts → call Ollama HTTP API (or BYOK LLM).
- [ ] Enforce 2–3 sentence output in prompt; truncate on token limits.

### 2.5 Service orchestration

- [ ] Create `src/services/rag_service.py`: `run_rag(title, description) -> (summary, ticket_ids)`.
- [ ] Update `src/services/triage_service.py`: after classify, if `RAG_ENABLED`, call `rag_service`; merge into `TicketStatusResponse`.
- [ ] On RAG failure: log warning; set empty RAG fields; keep routing result.

### 2.6 API schema & callback

- [ ] Update `src/api/v1/schemas.py` `TicketStatusResponse`:
  - `rag_resolution_summary: str = ""`
  - `similar_past_tickets: list[str] = []`
- [ ] Ensure `callback_service` serializes new fields (automatic via `model_dump` if on schema).
- [ ] Update `tests/test_api.py` for RAG fields (stub rag_service in tests).

### 2.7 Tests & validation

- [ ] `tests/test_rag_service.py` with mocked Pinecone and Ollama.
- [ ] `tests/test_embeddings.py` dimension sanity check.
- [ ] Manual: seed Pinecone → POST triage → GET shows summary + IDs.

---

## Phase 3 — n8n + Jira (orchestration)

Can start after Phase 2 fields exist on GET/callback (or stub empty fields earlier).

- [ ] Export `integrations/n8n/workflow-jira-triage-poll.json` per [TRD §5](TRD.md).
- [ ] Add `jira-team-mapping.example.json` for `assigned_team` → assignee/component.
- [ ] Update workflow Jira **Add Comment** node to include `rag_resolution_summary` and `similar_past_tickets`.
- [ ] Document Jira Cloud credentials + ngrok for local dev in `integrations/n8n/README.md`.
- [ ] End-to-end test: create Jira issue → comment appears with RAG text.

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
