"""Tests for Mermaid flowchart helpers and generator."""

from unittest.mock import MagicMock

import pytest

from src.rag.flowchart_generator import (
    FlowchartGenerator,
    extract_mermaid,
    validate_mermaid,
)
from src.rag.retriever import RetrievalContext


def test_extract_mermaid_from_fence():
    raw = "```mermaid\nflowchart TD\n  A --> B\n```"
    assert extract_mermaid(raw).startswith("flowchart TD")


def test_extract_mermaid_plain():
    raw = "flowchart LR\n  A --> B"
    assert extract_mermaid(raw) == raw


def test_validate_mermaid_accepts_valid():
    text = "flowchart TD\n  A[Start] --> B{Check}\n  B --> C[Done]"
    assert validate_mermaid(text, max_nodes=15) is True


def test_validate_mermaid_rejects_missing_header():
    assert validate_mermaid("graph TD\n  A --> B", max_nodes=15) is False


def test_generate_problem_flowchart(mock_llm):
    mock_llm.chat.return_value = "flowchart TD\n  A[VPN drop] --> B[Check auth]"
    gen = FlowchartGenerator(llm_client=mock_llm)
    result = gen.generate_problem_flowchart("VPN drops", "User loses connection")
    assert result.startswith("flowchart TD")
    mock_llm.chat.assert_called()


def test_generate_resolution_flowchart_with_contexts(mock_llm):
    mock_llm.chat.return_value = "flowchart TD\n  A[Issue] --> B[Renew cert]"
    gen = FlowchartGenerator(llm_client=mock_llm)
    contexts = [
        RetrievalContext(
            ticket_id="DEMO-1",
            title="VPN",
            description="drops",
            resolution_text="renew cert",
            team="Network",
            score=0.9,
        )
    ]
    result = gen.generate_resolution_flowchart("VPN drops", "User issue", contexts)
    assert "flowchart TD" in result


@pytest.fixture
def mock_llm():
    return MagicMock()
