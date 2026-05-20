# Technical Requirement Document (TRD)

## 1. Technology Stack
* Framework: FastAPI (Python 3.10+)
* Asynchronous Task Queue: BackgroundTasks (built into FastAPI for Phase 1 simplicity)
* Machine Learning: Scikit-learn or Hugging Face Optimum (for a lightweight, local NLP classifier)
* Deployment Environment: Local containerization (Docker)

## 2. API Specifications

### POST /api/v1/triage
Receives the raw ticket data from the ticketing system webhook.
* Request Payload (JSON):
  - ticket_id: string
  - title: string
  - description: string
  - created_at: datetime
* Response (JSON): Returns 202 Accepted immediately.

### GET /api/v1/triage/{ticket_id}
Retrieves the classification result.
* Response (JSON): Returns ticket_id, assigned_team, confidence_score, requires_hitl (boolean), and status.

## 3. ML Model Strategy (Phase 1)

### 3.1 Implemented runtime (this repository)

* **Classifier:** Hugging Face `zero-shot-classification` pipeline with a local pretrained model (`ZS_MODEL_NAME`, default `valhalla/distilbart-mnli-12-1`). Candidate routing targets are defined by **`CANDIDATE_LABELS`** (comma-separated environment variable). Inference uses `torch` + `transformers` locally (no per-ticket calls to external LLM APIs).
* **Text preprocessing:** Concatenate title and description, lowercase, strip punctuation, normalize whitespace, optional truncation before tokenization (`src/models/preprocessor.py`).
* **HITL:** `requires_hitl` when the top-label confidence is below **`HITL_THRESHOLD`** (default `0.80`).

### 3.2 Optional offline alternative (TF-IDF + Logistic Regression)

* `src/models/train.py` can train a TF-IDF vectorizer and Logistic Regression on synthetic data and write `pretrained_model.pkl` / `vectorizer.pkl` (`MODEL_PATH`, `VECTORIZER_PATH`). This path is **not** connected to `MLClassifier` at runtime by default; it remains available for experiments or a future switch to a sklearn-only stack.

### 3.3 Original design sketch (superseded for runtime by 3.1)

The following was the initial lightweight sketch; latency and stack should be validated on target hardware when using the zero-shot runtime:

* Vectorization: TF-IDF Vectorizer or a local small embedding model.
* Classifier: multi-class Logistic Regression or Linear SVM trained on a synthetic dataset.

## 4. Architectural Workflow (Phase 1)
1. Ingestion: Ticketing system triggers webhook. FastAPI validates payload.
2. Immediate Response: FastAPI returns 202 Accepted instantly.
3. Local Execution: Background worker processes text and runs local ML classifier.
4. Routing Callback: After triage, the service **POSTs** JSON to ``TRIAGE_CALLBACK_URL`` (if set) with ``ticket_id``, ``assigned_team``, ``confidence_score``, ``requires_hitl``, and ``status``. The ticketing platform uses ``requires_hitl`` and scores for routing vs manual review.

## 5. Project Structure

```
smart-triage-engine/
├── docs/
│   ├── PRD.md                          # Product Requirement Document
│   └── TRD.md                          # Technical Requirement Document
├── src/
│   ├── __init__.py
│   ├── main.py                         # FastAPI application entry point
│   ├── config.py                       # Configuration and environment variables
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── deps.py                 # Optional X-API-Key verification for POST /triage
│   │       ├── routes.py               # API endpoint definitions (POST /triage, GET /triage/{ticket_id})
│   │       └── schemas.py              # Pydantic models for request/response validation
│   ├── models/
│   │   ├── __init__.py
│   │   ├── ml_classifier.py            # ML classifier: HF zero-shot (runtime)
│   │   ├── train.py                    # Optional TF-IDF + LR training to pickle artifacts
│   │   └── preprocessor.py             # Text preprocessing for classification
│   ├── services/
│   │   ├── __init__.py
│   │   ├── triage_service.py           # Core triage logic, confidence scoring, HITL flagging
│   │   ├── callback_service.py         # Outbound HTTP callback to ticketing platform
│   │   └── cache_service.py            # In-memory cache for ticket classifications
│   └── data/
│       ├── training_data.csv           # Synthetic training dataset for ML model
│       ├── validation_set.csv          # Labeled rows for accuracy evaluation (scripts/evaluate_accuracy.py)
│       ├── pretrained_model.pkl        # Serialized ML classifier
│       └── vectorizer.pkl              # Serialized TF-IDF vectorizer
├── tests/
│   ├── __init__.py
│   ├── test_api.py                     # API endpoint tests
│   ├── test_ml_model.py                # ML model and preprocessing tests
│   └── test_services.py                # Service logic tests
├── requirements.txt                    # Python dependencies (FastAPI, scikit-learn, pydantic, etc.)
├── Dockerfile                          # Docker container configuration
├── docker-compose.yml                  # Multi-container orchestration (optional for Phase 1)
├── .env.example                        # Example environment variables
├── .gitignore                          # Git exclusion rules
└── README.md                           # Project overview and setup instructions
```

### Directory Descriptions

**docs/** — Documentation folder containing PRD and TRD documents for requirements and technical specifications.

**src/** — Main application source code.
- `main.py`: FastAPI application initialization, middleware setup, and server configuration.
- `config.py`: Centralized configuration management (model paths, confidence thresholds, API settings).
- `api/v1/`: API v1 endpoints and request/response schema definitions using Pydantic.
- `models/`: Machine learning components including the classifier and text preprocessing pipeline.
- `services/`: Business logic layer handling triage operations, confidence scoring, and result caching.
- `data/`: Pre-trained model artifacts and training data.

**tests/** — Comprehensive test suite covering API endpoints, ML model behavior, and service logic.

**Root Configuration Files:**
- `requirements.txt`: Python package dependencies (FastAPI, uvicorn, scikit-learn, pandas, pydantic, transformers, torch).
- `Dockerfile`: Container image definition for local deployment and reproducibility.
- `docker-compose.yml`: (Optional) For potential integration with other services in future phases.
- `.env.example`: Template for environment variables (confidence threshold, model paths, logging level).
- `.gitignore`: Excludes virtual environments, compiled models, and sensitive data.
- `README.md`: Quick start guide and developer documentation.

## 6. Implementation status (Phase 1)

| Area | Status | Notes |
|------|--------|--------|
| FastAPI app, config, CORS | Implemented | [`src/main.py`](src/main.py), [`src/config.py`](src/config.py) |
| POST /api/v1/triage + validation | Implemented | Optional ``X-API-Key`` when ``WEBHOOK_INGEST_API_KEY`` is set ([`deps.py`](src/api/v1/deps.py)) |
| Idempotent POST by ``ticket_id`` | Implemented | Skips re-queue when status is ``completed``, ``failed``, or ``processing`` ([`routes.py`](src/api/v1/routes.py)) |
| GET /api/v1/triage/{ticket_id} | Implemented | |
| Text preprocessor | Implemented | Lowercase, punctuation, whitespace ([`preprocessor.py`](src/models/preprocessor.py)) |
| Runtime ML (zero-shot) | Implemented | [`ml_classifier.py`](src/models/ml_classifier.py) |
| TF-IDF + LR training script | Optional / offline | [`train.py`](src/models/train.py), not default runtime |
| Background triage + cache | Implemented | Shared cache + lazy classifier ([`triage_service.py`](src/services/triage_service.py)) |
| HITL at configurable threshold | Implemented | ``HITL_THRESHOLD`` |
| Outbound routing callback | Implemented | ``TRIAGE_CALLBACK_URL`` ([`callback_service.py`](src/services/callback_service.py)) |
| Unit / integration tests | Partial | Core paths covered under [`tests/`](tests/) |
| Docker image | Implemented | [`Dockerfile`](Dockerfile) |
| PRD latency (<200ms) | Manual / env-specific | Use [`scripts/latency_sample.py`](scripts/latency_sample.py); measure after warm-up on target hardware |
| PRD accuracy (>=85%) | Manual | Use [`scripts/evaluate_accuracy.py`](scripts/evaluate_accuracy.py) with [`validation_set.csv`](src/data/validation_set.csv) or your own labels |
| Durable store (Redis/SQLite) | Deferred | In-memory cache only |
| Ticketing simulator contract (HMAC, etc.) | Documented | README “Simulator integration”; extend if the simulator mandates more than ``X-API-Key`` |
| Jira + n8n orchestration | Planned | Guide: [INTEGRATION_N8N_JIRA.md](INTEGRATION_N8N_JIRA.md); build prompt: [HANDOFF_N8N_JIRA_PROMPT.md](HANDOFF_N8N_JIRA_PROMPT.md); artifacts target ``integrations/n8n/`` |