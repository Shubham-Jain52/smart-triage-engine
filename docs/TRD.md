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
To keep latency under 200ms and maintain absolute privacy:
* Text Preprocessing: Concatenate title and description, convert to lowercase, and strip punctuation.
* Vectorization: TF-IDF Vectorizer or a local small embedding model.
* Classifier: A multi-class Logistic Regression or Linear SVM trained on a synthetic dataset of common IT categories.

## 4. Architectural Workflow (Phase 1)
1. Ingestion: Ticketing system triggers webhook. FastAPI validates payload.
2. Immediate Response: FastAPI returns 202 Accepted instantly.
3. Local Execution: Background worker processes text and runs local ML classifier.
4. Routing Callback: System executes callback to ticketing platform based on confidence score (>80% assigns team, <80% flags HITL).

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
│   │       ├── routes.py               # API endpoint definitions (POST /triage, GET /triage/{ticket_id})
│   │       └── schemas.py              # Pydantic models for request/response validation
│   ├── models/
│   │   ├── __init__.py
│   │   ├── ml_classifier.py            # ML classifier wrapper (Logistic Regression / Linear SVM)
│   │   └── preprocessor.py             # Text preprocessing, vectorization (TF-IDF)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── triage_service.py           # Core triage logic, confidence scoring, HITL flagging
│   │   └── cache_service.py            # In-memory cache for ticket classifications
│   └── data/
│       ├── training_data.csv           # Synthetic training dataset for ML model
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
- `requirements.txt`: Python package dependencies (FastAPI, uvicorn, scikit-learn, pandas, pydantic).
- `Dockerfile`: Container image definition for local deployment and reproducibility.
- `docker-compose.yml`: (Optional) For potential integration with other services in future phases.
- `.env.example`: Template for environment variables (confidence threshold, model paths, logging level).
- `.gitignore`: Excludes virtual environments, compiled models, and sensitive data.
- `README.md`: Quick start guide and developer documentation.

## 6. Phase 1 Development Checklist
- [ ] Set up FastAPI application structure with config management
- [ ] Implement POST /api/v1/triage webhook endpoint with payload validation
- [ ] Implement GET /api/v1/triage/{ticket_id} result retrieval endpoint
- [ ] Build text preprocessor (lowercase, punctuation removal, concatenation)
- [ ] Create TF-IDF vectorizer and train Logistic Regression classifier
- [ ] Integrate ML classifier with async background task processing
- [ ] Implement confidence scoring and 80% HITL flagging logic
- [ ] Add in-memory caching for classification results
- [ ] Write comprehensive unit and integration tests
- [ ] Create Docker containerization
- [ ] Validate latency (<200ms) and accuracy (>85%) requirements
- [ ] Document API usage and deployment instructions