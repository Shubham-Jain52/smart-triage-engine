"""Tests for Pinecone ticket retriever."""

from unittest.mock import MagicMock, patch

import pytest


@patch("src.rag.retriever.embed")
def test_retrieve_returns_contexts(mock_embed):
    mock_embed.return_value = [0.1] * 384
    mock_pc = MagicMock()
    mock_pc.query.return_value = [
        {
            "id": "DEMO-1",
            "score": 0.92,
            "metadata": {
                "ticket_id": "DEMO-1",
                "title": "VPN drops",
                "description": "remote user",
                "resolution_text": "renew cert",
                "team": "Network",
            },
        }
    ]

    from src.rag.retriever import TicketRetriever

    retriever = TicketRetriever(pinecone_client=mock_pc)
    result = retriever.retrieve("VPN issue", "cannot connect")

    assert result.similar_past_tickets == ["DEMO-1"]
    assert len(result.contexts) == 1
    assert result.contexts[0].resolution_text == "renew cert"
    mock_pc.query.assert_called_once()
