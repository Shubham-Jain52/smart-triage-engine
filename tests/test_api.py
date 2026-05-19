"""API endpoint tests."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from src.main import app
from src.api.v1 import routes

client = TestClient(app)


class TestTriageEndpoints:
    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()
    
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_create_triage_accepted(self):
        payload = {
            "ticket_id": "TICKET-001",
            "title": "Network issue",
            "description": "Cannot connect to VPN",
            "created_at": datetime.now().isoformat()
        }
        response = client.post("/api/v1/triage", json=payload)
        assert response.status_code == 202
        assert response.json()["ticket_id"] == "TICKET-001"
        assert response.json()["status"] == "processing"

    def test_create_triage_sets_processing_cache(self, monkeypatch):
        def dummy_process_triage(request):
            return None

        monkeypatch.setattr(routes.triage_service, "process_triage", dummy_process_triage)
        routes.cache_service.clear()

        payload = {
            "ticket_id": "TICKET-002",
            "title": "Email outage",
            "description": "Cannot send or receive email",
            "created_at": datetime.now().isoformat()
        }
        response = client.post("/api/v1/triage", json=payload)
        assert response.status_code == 202

        cached = routes.cache_service.get("TICKET-002")
        assert cached is not None
        assert cached.status == "processing"
        assert cached.assigned_team == "pending"

    def test_get_triage_not_found(self):
        response = client.get("/api/v1/triage/NONEXISTENT")
        assert response.status_code == 404
