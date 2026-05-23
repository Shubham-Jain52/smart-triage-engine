"""Tests for Phase 2 RAG service."""

from unittest.mock import MagicMock

import pytest

from src.rag.retriever import RetrievalContext, RetrievalResult
from src.services.rag_service import RagResult, RagService


@pytest.fixture
def sample_retrieval():
    return RetrievalResult(
        similar_past_tickets=["DEMO-1"],
        contexts=[
            RetrievalContext(
                ticket_id="DEMO-1",
                title="VPN drops",
                description="remote access",
                resolution_text="renewed certificate",
                team="Network",
                score=0.88,
            )
        ],
    )


def test_run_rag_returns_diagrams(monkeypatch, sample_retrieval):
    monkeypatch.setenv("RAG_ENABLED", "true")
    monkeypatch.setenv("PINECONE_API_KEY", "pk-test")
    from src.config import get_settings

    get_settings.cache_clear()

    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = sample_retrieval
    mock_flowchart = MagicMock()
    mock_flowchart.generate_problem_flowchart.return_value = "flowchart TD\n  A --> B"
    mock_flowchart.generate_resolution_flowchart.return_value = "flowchart TD\n  P --> Q"
    mock_summary = MagicMock()
    mock_summary.generate_summary.return_value = "Similar VPN issues were fixed by renewing certs."

    service = RagService(
        retriever=mock_retriever,
        flowchart_generator=mock_flowchart,
        summary_generator=mock_summary,
    )
    result = service.run_rag("VPN drops", "User loses connection")

    assert isinstance(result, RagResult)
    assert result.problem_flowchart_mermaid.startswith("flowchart TD")
    assert result.resolution_flowchart_mermaid.startswith("flowchart TD")
    assert "VPN" in result.rag_resolution_summary or "cert" in result.rag_resolution_summary.lower()
    assert result.similar_past_tickets == ["DEMO-1"]


def test_run_rag_disabled_returns_empty(monkeypatch):
    monkeypatch.setenv("RAG_ENABLED", "false")
    from src.config import get_settings

    get_settings.cache_clear()

    service = RagService(retriever=MagicMock())
    result = service.run_rag("title", "desc")
    assert result.problem_flowchart_mermaid == ""
    assert result.similar_past_tickets == []
    service.retriever.retrieve.assert_not_called()


def test_run_rag_failure_returns_empty(monkeypatch):
    monkeypatch.setenv("RAG_ENABLED", "true")
    monkeypatch.setenv("PINECONE_API_KEY", "pk-test")
    from src.config import get_settings

    get_settings.cache_clear()

    mock_retriever = MagicMock()
    mock_retriever.retrieve.side_effect = RuntimeError("Pinecone down")

    service = RagService(retriever=mock_retriever)
    result = service.run_rag("title", "desc")
    assert result == RagResult()
