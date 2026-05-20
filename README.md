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

Retrieve classification result (`completed`, `failed`, or `processing`).

## Outbound routing callback

When `TRIAGE_CALLBACK_URL` is non-empty, after each triage finishes (`completed` or `failed`) the service **POSTs** JSON to that URL with the same fields as GET: `ticket_id`, `assigned_team`, `confidence_score`, `requires_hitl`, `status`.

- `TRIAGE_CALLBACK_API_KEY`: if set, sent as `X-API-Key` on the outbound request.
- `TRIAGE_CALLBACK_TIMEOUT_SECONDS`, `TRIAGE_CALLBACK_RETRIES`: control httpx timeout and retry count (retries are best-effort; failures are logged and do not roll back the cached result).

## Jira + n8n integration (demo / production glue)

The triage microservice does **not** update Jira by itself. Use **n8n** (or similar) to:

1. Trigger on Jira issue created → **POST** `/api/v1/triage`
2. **Poll** `GET /api/v1/triage/{issue_key}` *or* receive **`TRIAGE_CALLBACK_URL`** on an n8n Webhook
3. Update the Jira issue (assignee, component, labels) from `assigned_team` and `requires_hitl`

**Guides:**

- [docs/INTEGRATION_N8N_JIRA.md](docs/INTEGRATION_N8N_JIRA.md) — architecture, API mapping, Pattern A (poll) vs B (callback)
- [docs/HANDOFF_N8N_JIRA_PROMPT.md](docs/HANDOFF_N8N_JIRA_PROMPT.md) — copy-paste prompt for a new chat to build workflow JSON under `integrations/n8n/`

**Microservice status:** Phase 1 API is **ready** for this integration; n8n workflows are the next build step (see `integrations/n8n/README.md`).

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

## Documentation

- [docs/PRD.md](docs/PRD.md) — product requirements
- [docs/TRD.md](docs/TRD.md) — technical requirements and implementation notes
- [docs/INTEGRATION_N8N_JIRA.md](docs/INTEGRATION_N8N_JIRA.md) — Jira + n8n integration
- [docs/HANDOFF_N8N_JIRA_PROMPT.md](docs/HANDOFF_N8N_JIRA_PROMPT.md) — handoff prompt for building n8n workflows
