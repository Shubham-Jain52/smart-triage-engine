# Smart Triage Engine

AI-powered ticket classification system built with FastAPI. Incoming tickets are accepted on a webhook-style endpoint, classified in a **background task**, and read back by id from an in-memory cache. When configured, the service **POSTs** the final triage payload to a **routing callback URL** for the ticketing platform (TRD workflow step 4).

## Python version

Use **Python 3.10, 3.11, or 3.12** (see `.python-version` for a suggested local pin). **Python 3.13** often lacks wheels for older pinned `scikit-learn` and may try to compile from source.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## ML runtime (Phase 1)

The live classifier is a **local Hugging Face zero-shot** pipeline (`transformers` + `torch`). Team names are whatever you set in **`CANDIDATE_LABELS`** (comma-separated env var); the model picks the best label and returns its score for HITL (`HITL_THRESHOLD`, default `0.80`).

Optional **TF-IDF + Logistic Regression** training (not wired into the API by default) lives in `src/models/train.py` for experiments or a future sklearn-based classifier.

## Quick Start

1. Copy env template and adjust labels if needed:

```bash
cp .env.example .env
```

2. Run the application from the project root:

```bash
uvicorn src.main:app --reload
```

3. Smoke test:

```bash
curl -s http://127.0.0.1:8000/health
```

## API Endpoints

### POST /api/v1/triage

Submit a ticket for classification. Returns **202** immediately; processing runs in a background task.

JSON body: `ticket_id`, `title`, `description`, `created_at` (ISO datetime).

**Idempotency:** If a ticket is already `completed` or `failed`, a repeat POST returns **202** with `status` set to that terminal state and **does not** enqueue another triage. If status is `processing`, repeat POST returns **202** with `processing` and does not enqueue a duplicate task.

**Inbound auth (optional):** If `WEBHOOK_INGEST_API_KEY` is set, clients must send header `X-API-Key: <value>`. Leave unset for open local development.

### GET /api/v1/triage/{ticket_id}

Retrieve classification result (`completed`, `failed`, or `processing`). When `RAG_ENABLED=true`, completed responses also include `problem_flowchart_mermaid`, `resolution_flowchart_mermaid`, `rag_resolution_summary`, and audit-only `similar_past_tickets`.

## Outbound routing callback

When `TRIAGE_CALLBACK_URL` is non-empty, after each triage finishes (`completed` or `failed`) the service **POSTs** JSON to that URL with the same fields as GET (including RAG flowchart fields when enabled).

- `TRIAGE_CALLBACK_API_KEY`: if set, sent as `X-API-Key` on the outbound request.
- `TRIAGE_CALLBACK_TIMEOUT_SECONDS`, `TRIAGE_CALLBACK_RETRIES`: control httpx timeout and retry count (retries are best-effort; failures are logged and do not roll back the cached result).

## Jira integration (Phase 3 — Python worker)

The triage service does **not** update Jira by itself. Run the **Python worker**:

```bash
# Process one issue (manual or cron after Jira Automation)
PYTHONPATH=. python scripts/run_jira_worker.py --issue PROJ-42

# Poll for new issues every N minutes (cron fallback)
PYTHONPATH=. python scripts/run_jira_worker.py --once
```

The worker:

1. Fetches the Jira issue → **POST** `/api/v1/triage` → poll **GET** result
2. Updates assignee/component/labels from `assigned_team` and `requires_hitl` (see team mapping JSON)
3. Posts an internal comment with **Mermaid flowcharts** (problem + resolution maps)

See [docs/PHASE3_SETUP.md](docs/PHASE3_SETUP.md). Optional n8n path: [docs/INTEGRATION_N8N_JIRA.md](docs/INTEGRATION_N8N_JIRA.md).

## Phase 4: Local Stack Packaging (Docker Compose)

The entire application stack—including the **Triage API**, **n8n workflow automation**, and local **Ollama inference**—can be started with a single command:

```bash
# 1. Start the core stack (Triage API + n8n)
docker-compose up --build

# 2. (Optional) Start with local Ollama service enabled for flowchart generation
docker-compose --profile llm-local up --build
```

### Stack Components

| Service | Port | Purpose / URL |
|---------|------|---------------|
| `triage-api` | `8000` | FastAPI webhook endpoint: `http://localhost:8000/health` |
| `n8n` | `5678` | Local automation designer: `http://localhost:5678/` |
| `ollama` | `11434` | (Optional) Local LLM endpoint: `http://localhost:11434/` |

### Key Compose Features

1. **Persisted Caches:** Hugging Face model weights (`valhalla/distilbart-mnli-12-1` and `sentence-transformers/all-MiniLM-L6-v2`) are stored in a host-mounted `.cache/` directory to prevent redownloads across container runs.
2. **Network Communications:** Within the docker-compose network, other containers (like `n8n`) can reach the API via the service hostname, i.e., `TRIAGE_API_URL=http://triage-api:8000`.
3. **Health Checks:** Self-monitoring health checks are included for both the API (`/health`) and n8n (`/healthz`).


## Simulator integration

Align with your ticketing simulator contract:

| Mechanism | This service |
|-----------|----------------|
| Ingest webhook auth | Optional `WEBHOOK_INGEST_API_KEY` + `X-API-Key` on POST `/api/v1/triage` |
| Idempotent ticket submission | Same `ticket_id` while `processing` / after terminal state does not double-enqueue |
| Outbound result delivery | POST to `TRIAGE_CALLBACK_URL` with optional `X-API-Key` |
| HMAC / custom signatures | Not built-in; add middleware or document if the simulator requires it |

## Configuration

See [`.env.example`](.env.example). Important keys:

| Variable | Purpose |
|----------|---------|
| `CANDIDATE_LABELS` | Comma-separated team labels for zero-shot routing |
| `ZS_MODEL_NAME` | Hugging Face model id for zero-shot classification |
| `HITL_THRESHOLD` | Confidence below this marks `requires_hitl` (default `0.80`) |
| `WEBHOOK_INGEST_API_KEY` | If set, POST `/api/v1/triage` requires matching `X-API-Key` |
| `TRIAGE_CALLBACK_URL` | If set, POST triage results here when done |
| `TRIAGE_CALLBACK_API_KEY` | Optional outbound `X-API-Key` for the callback |

## Latency (PRD)

The PRD targets **under 200 ms** for the **classification layer** (model inference on preprocessed text), not including first-time model download or process startup.

**How to measure meaningfully:**

1. Install full `requirements.txt` and run a **warm-up** classify (or start the server and process one throwaway ticket).
2. Run [`scripts/latency_sample.py`](scripts/latency_sample.py) and read the **“classify() only”** line after warm-up, or wrap repeated `classify()` calls in a tight loop and take **p50/p95** with `time.perf_counter`.
3. Compare to 200 ms on the **same** CPU/GPU class you deploy on. Cold JVM-style “first inference” is often much slower than steady state.

```bash
PYTHONPATH=. python scripts/latency_sample.py
```

## Accuracy (PRD)

PRD asks for **>= 85%** correct routing on a validation set. Use a labeled CSV (`title`, `description`, `expected_team`) aligned with your `CANDIDATE_LABELS`.

A small starter set lives at [`src/data/validation_set.csv`](src/data/validation_set.csv). Evaluate with:

```bash
PYTHONPATH=. python scripts/evaluate_accuracy.py
PYTHONPATH=. python scripts/evaluate_accuracy.py path/to/your_labeled.csv
```

This runs the same `MLClassifier` as production; results depend on model, labels, and ticket wording.

## Phase 5: Pinecone cold-start

Backfill Pinecone before enabling RAG. **No Jira required** for local dev — uses bundled dummy CSV by default; switch to `--source jira` later.

```bash
PYTHONPATH=. python scripts/setup_pinecone_index.py
PYTHONPATH=. python scripts/ingest.py                    # dummy CSV
PYTHONPATH=. python scripts/ingest.py --source jira      # when Jira is ready
PYTHONPATH=. python scripts/pinecone_smoke_query.py "VPN issue"
```

See [docs/PHASE5_SETUP.md](docs/PHASE5_SETUP.md).

## Phase 2: Enable RAG flowcharts

After Pinecone is populated (Phase 5), enable live retrieval + Mermaid generation:

```bash
# .env
RAG_ENABLED=true
PINECONE_API_KEY=your-key
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Start Ollama and pull model: ollama pull llama3.2
uvicorn src.main:app --reload
```

POST a ticket → GET result includes `problem_flowchart_mermaid`, `resolution_flowchart_mermaid`, `rag_resolution_summary`, and audit-only `similar_past_tickets`.

## Keeping Pinecone fresh (Phase 3.1)

After Phase 5 cold start, enable continuous re-ingest when Jira issues are resolved:

```bash
# .env
INGEST_ON_RESOLVE_ENABLED=true

# Jira Automation → POST /api/v1/ingest/resolved  (primary)
# Cron fallback:
PYTHONPATH=. python scripts/poll_resolved_ingest.py --once
```

See [docs/PHASE3_1_ON_RESOLVE_INGEST.md](docs/PHASE3_1_ON_RESOLVE_INGEST.md).

## Documentation

- [docs/PRD.md](docs/PRD.md) — product requirements (Phases 1–5)
- [docs/TRD.md](docs/TRD.md) — technical architecture, API contracts, RAG flow
- [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) — Phase 2/4 build checklist and target folder structure
- [docs/PHASE2_SETUP.md](docs/PHASE2_SETUP.md) — enable RAG flowcharts (Ollama + Pinecone)
- [docs/PHASE3_SETUP.md](docs/PHASE3_SETUP.md) — Jira worker (routing + flowchart comments)
- [docs/PHASE3_1_ON_RESOLVE_INGEST.md](docs/PHASE3_1_ON_RESOLVE_INGEST.md) — on-resolve continuous re-ingest
- [docs/INTEGRATION_N8N_JIRA.md](docs/INTEGRATION_N8N_JIRA.md) — Jira + n8n integration
- [docs/HANDOFF_N8N_JIRA_PROMPT.md](docs/HANDOFF_N8N_JIRA_PROMPT.md) — handoff prompt for building n8n workflows
