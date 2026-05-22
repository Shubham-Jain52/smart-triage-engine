"""Tests for Pinecone client (mocked SDK)."""

from unittest.mock import MagicMock, patch

from src.config import get_settings


def test_upsert_and_query(monkeypatch):
    monkeypatch.setenv("PINECONE_API_KEY", "test-key")
    monkeypatch.setenv("PINECONE_INDEX_NAME", "test-index")
    get_settings.cache_clear()

    mock_index = MagicMock()
    mock_match = MagicMock()
    mock_match.id = "PROJ-1"
    mock_match.score = 0.95
    mock_match.metadata = {"ticket_id": "PROJ-1", "resolution_text": "fixed VPN"}
    mock_index.query.return_value = MagicMock(matches=[mock_match])

    mock_pc = MagicMock()
    mock_pc.Index.return_value = mock_index

    with patch("pinecone.Pinecone", return_value=mock_pc):
        from src.rag.pinecone_client import PineconeClient

        client = PineconeClient()
        n = client.upsert_records([{"id": "PROJ-1", "values": [0.1] * 384, "metadata": {}}])
        assert n == 1
        mock_index.upsert.assert_called_once()

        results = client.query([0.1] * 384, top_k=3)
        assert results[0]["id"] == "PROJ-1"
        assert results[0]["metadata"]["resolution_text"] == "fixed VPN"
