"""API endpoint tests."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from src.config import get_settings
from src.main import app
from src.api.v1 import routes
from src.models.ml_classifier import MLClassifier

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

    def test_post_then_get_shows_completed_when_classifier_stubbed(self, monkeypatch):
        """Background task updates the same cache the GET handler reads."""
        def fake_load(self):
            self._pipeline = lambda text, candidate_labels: {
                "labels": ["DevOps"],
                "scores": [0.95],
            }

        monkeypatch.setattr(MLClassifier, "_load_pipeline", fake_load)
        routes.triage_service._classifier = None
        routes.cache_service.clear()

        ticket_id = "TICKET-E2E-001"
        payload = {
            "ticket_id": ticket_id,
            "title": "CI pipeline",
            "description": "Deploy job failing on runner 3",
            "created_at": datetime.now().isoformat(),
        }
        post_resp = client.post("/api/v1/triage", json=payload)
        assert post_resp.status_code == 202

        get_resp = client.get(f"/api/v1/triage/{ticket_id}")
        assert get_resp.status_code == 200
        body = get_resp.json()
        assert body["status"] == "completed"
        assert body["assigned_team"] == "DevOps"
        assert body["requires_hitl"] is False
        assert abs(body["confidence_score"] - 0.95) < 1e-9

    def test_post_invokes_routing_callback_on_completion(self, monkeypatch):
        def fake_load(self):
            self._pipeline = lambda text, candidate_labels: {
                "labels": ["DevOps"],
                "scores": [0.95],
            }

        monkeypatch.setattr(MLClassifier, "_load_pipeline", fake_load)
        mock_cb = MagicMock()
        routes.triage_service.callback_service = mock_cb
        routes.triage_service._classifier = None
        routes.cache_service.clear()

        ticket_id = "TICKET-CB-1"
        payload = {
            "ticket_id": ticket_id,
            "title": "Deploy",
            "description": "Helm upgrade failed",
            "created_at": datetime.now().isoformat(),
        }
        assert client.post("/api/v1/triage", json=payload).status_code == 202
        assert client.get(f"/api/v1/triage/{ticket_id}").json()["status"] == "completed"
        mock_cb.notify_triage_result.assert_called_once()
        arg = mock_cb.notify_triage_result.call_args[0][0]
        assert arg.ticket_id == ticket_id
        assert arg.status == "completed"

    def test_post_requires_x_api_key_when_configured(self, monkeypatch):
        monkeypatch.setenv("WEBHOOK_INGEST_API_KEY", "ingest-secret")
        get_settings.cache_clear()

        payload = {
            "ticket_id": "TICKET-AUTH",
            "title": "t",
            "description": "d",
            "created_at": datetime.now().isoformat(),
        }
        assert client.post("/api/v1/triage", json=payload).status_code == 401
        r = client.post(
            "/api/v1/triage",
            json=payload,
            headers={"X-API-Key": "ingest-secret"},
        )
        assert r.status_code == 202

    def test_post_idempotent_skips_second_enqueue(self, monkeypatch):
        def fake_load(self):
            self._pipeline = lambda text, candidate_labels: {
                "labels": ["DevOps"],
                "scores": [0.95],
            }

        monkeypatch.setattr(MLClassifier, "_load_pipeline", fake_load)
        mock_cb = MagicMock()
        routes.triage_service.callback_service = mock_cb
        routes.triage_service._classifier = None
        routes.cache_service.clear()

        ticket_id = "TICKET-IDEM"
        payload = {
            "ticket_id": ticket_id,
            "title": "Deploy",
            "description": "Helm upgrade failed",
            "created_at": datetime.now().isoformat(),
        }
        assert client.post("/api/v1/triage", json=payload).status_code == 202
        assert client.get(f"/api/v1/triage/{ticket_id}").json()["status"] == "completed"
        mock_cb.reset_mock()
        r2 = client.post("/api/v1/triage", json=payload)
        assert r2.status_code == 202
        assert r2.json()["status"] == "completed"
        mock_cb.notify_triage_result.assert_not_called()

    def test_ingest_resolved_success(self, monkeypatch):
        monkeypatch.setenv("INGEST_ON_RESOLVE_ENABLED", "true")
        get_settings.cache_clear()

        from src.services.resolve_ingest_service import IngestResult

        mock_result = IngestResult(ticket_id="PROJ-99", status="ingested", message="upserted 1 vector(s)")
        routes.resolve_ingest_service.ingest_resolved_ticket = MagicMock(return_value=mock_result)

        response = client.post("/api/v1/ingest/resolved", json={"ticket_id": "PROJ-99"})
        assert response.status_code == 200
        body = response.json()
        assert body["ticket_id"] == "PROJ-99"
        assert body["status"] == "ingested"

    def test_ingest_resolved_requires_x_api_key_when_configured(self, monkeypatch):
        monkeypatch.setenv("WEBHOOK_INGEST_API_KEY", "ingest-secret")
        get_settings.cache_clear()

        assert client.post("/api/v1/ingest/resolved", json={"ticket_id": "PROJ-1"}).status_code == 401
        r = client.post(
            "/api/v1/ingest/resolved",
            json={"ticket_id": "PROJ-1"},
            headers={"X-API-Key": "ingest-secret"},
        )
        assert r.status_code == 200

    def test_triage_includes_rag_fields_when_enabled(self, monkeypatch):
        monkeypatch.setenv("RAG_ENABLED", "true")
        get_settings.cache_clear()

        from src.services.rag_service import RagResult

        def fake_load(self):
            self._pipeline = lambda text, candidate_labels: {
                "labels": ["DevOps"],
                "scores": [0.95],
            }

        monkeypatch.setattr(MLClassifier, "_load_pipeline", fake_load)

        mock_rag = MagicMock()
        mock_rag.run_rag.return_value = RagResult(
            problem_flowchart_mermaid="flowchart TD\n  A[VPN] --> B[Check]",
            resolution_flowchart_mermaid="flowchart TD\n  P[Past fix] --> Q[Done]",
            rag_resolution_summary="Renew certificate for VPN issues.",
            similar_past_tickets=["DEMO-1"],
        )
        routes.triage_service._rag_service = mock_rag
        routes.triage_service._classifier = None
        routes.cache_service.clear()

        ticket_id = "TICKET-RAG-1"
        payload = {
            "ticket_id": ticket_id,
            "title": "VPN issue",
            "description": "Connection drops",
            "created_at": datetime.now().isoformat(),
        }
        assert client.post("/api/v1/triage", json=payload).status_code == 202
        body = client.get(f"/api/v1/triage/{ticket_id}").json()
        assert body["status"] == "completed"
        assert body["problem_flowchart_mermaid"].startswith("flowchart TD")
        assert body["resolution_flowchart_mermaid"].startswith("flowchart TD")
        assert body["rag_resolution_summary"]
        assert body["similar_past_tickets"] == ["DEMO-1"]
        mock_rag.run_rag.assert_called_once()
