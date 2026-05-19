# Smart Triage Engine

AI-powered ticket classification system built with FastAPI.

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
uvicorn src.main:app --reload
```

## API Endpoints

### POST /api/v1/triage
Submit a ticket for classification.

### GET /api/v1/triage/{ticket_id}
Retrieve classification result.

## Configuration
Edit `.env` file to customize settings.
