# Smart Triage Engine

An AI-powered ticket classification system built with FastAPI that automatically routes support tickets to the appropriate teams based on content analysis.

## Features

- **Fast Classification**: Local ML model ensures sub-200ms response times
- **Privacy-First**: All processing happens locally, no external API calls
- **Async Processing**: Immediate 202 response with background classification
- **Confidence Scoring**: Automatically flags uncertain tickets for human review
- **Caching**: In-memory result caching for reduced processing time
- **Docker Support**: Easy deployment with containerization

## Tech Stack

- **Framework**: FastAPI
- **ML**: Scikit-learn (Logistic Regression/Linear SVM)
- **Deployment**: Docker
- **Task Queue**: FastAPI BackgroundTasks

## Project Structure

```
smart-triage-engine/
├── docs/                      # Documentation
├── src/                       # Application source code
│   ├── api/v1/               # API endpoints and schemas
│   ├── models/               # ML classifier and preprocessing
│   ├── services/             # Business logic (triage, caching)
│   ├── data/                 # ML models and training data
│   ├── config.py             # Configuration management
│   └── main.py               # FastAPI application
├── tests/                    # Test suite
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker configuration
└── docker-compose.yml        # Docker Compose configuration
```

## Quick Start

### Prerequisites

- Python 3.10+
- Docker (optional)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Shubham-Jain52/smart-triage-engine.git
cd smart-triage-engine
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy environment template:
```bash
cp .env.example .env
```

### Running Locally

```bash
uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`

### Running with Docker

```bash
docker-compose up
```

## API Endpoints

### POST /api/v1/triage

Submit a ticket for classification.

**Request**:
```json
{
  "ticket_id": "TICKET-001",
  "title": "Network connectivity issue",
  "description": "Unable to connect to corporate VPN",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Response** (202 Accepted):
```json
{
  "ticket_id": "TICKET-001",
  "status": "processing"
}
```

### GET /api/v1/triage/{ticket_id}

Retrieve classification result.

**Response**:
```json
{
  "ticket_id": "TICKET-001",
  "assigned_team": "Network Support",
  "confidence_score": 0.92,
  "requires_hitl": false,
  "status": "completed"
}
```

## Configuration

Edit `.env` file to customize:

- `CONFIDENCE_THRESHOLD`: Confidence level below which tickets require human review (default: 0.80)
- `LOG_LEVEL`: Logging level (default: INFO)
- `CACHE_ENABLED`: Enable result caching (default: true)
- `CACHE_TTL_SECONDS`: Cache expiration time (default: 3600)

## Testing

Run tests with pytest:

```bash
pytest
```

For coverage:
```bash
pytest --cov=src
```

## Development

### Adding New Dependencies

```bash
pip install package-name
pip freeze > requirements.txt
```

### Running Tests During Development

```bash
pytest --watch  # Requires pytest-watch
```

## Performance

- **Classification Latency**: < 200ms (local ML model)
- **API Response Time**: ~10-20ms (202 Accepted)
- **Cache Hit Rate**: Variable (depends on ticket distribution)

## Future Phases

- [ ] Integration with external ticketing systems
- [ ] Support for multiple ML models
- [ ] Database persistence for results
- [ ] Webhook callbacks for team routing
- [ ] Advanced confidence scoring
- [ ] A/B testing framework

## License

MIT License

## Contributing

Contributions are welcome! Please follow the existing code style and add tests for new features.
