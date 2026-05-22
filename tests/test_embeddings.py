"""Tests for embedding module (mocked model)."""

from unittest.mock import MagicMock, patch

import numpy as np


def test_embed_returns_list(monkeypatch):
    mock_model = MagicMock()
    mock_model.get_sentence_embedding_dimension.return_value = 384
    mock_model.encode.return_value = np.array([0.1, 0.2, 0.3], dtype=np.float32)

    monkeypatch.setattr("src.models.embeddings._get_model", lambda: mock_model)

    from src.models.embeddings import embed, embedding_dimension

    assert embedding_dimension() == 384
    vec = embed("test ticket")
    assert len(vec) == 3
    mock_model.encode.assert_called_once()
