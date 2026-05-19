"""API endpoint tests."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from src.main import app

client = TestClient(app)


class TestTriageEndpoints:
    """Test triage API endpoints."""
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_create_triage_accepted(self):
        """Test POST /api/v1/triage returns 202 Accepted."""
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
    
    def test_get_triage_not_found(self):
        """Test GET /api/v1/triage/{ticket_id} returns 404 for non-existent ticket."""
        response = client.get("/api/v1/triage/NONEXISTENT")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
