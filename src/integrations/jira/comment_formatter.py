"""Build Jira comments from triage results (Phase 3)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.api.v1.schemas import TicketStatusResponse
from src.config import get_settings


def format_triage_comment(result: TicketStatusResponse) -> Tuple[str, Dict[str, Any]]:
    """Return (plain_text, adf_body) for Jira comment API."""
    settings = get_settings()
    header = (
        f"[Auto-Triage] Team: {result.assigned_team} | "
        f"Confidence: {result.confidence_score:.2f} | HITL: {result.requires_hitl}"
    )
    lines: List[str] = [header]
    if result.rag_resolution_summary:
        lines.append(result.rag_resolution_summary)

    if result.problem_flowchart_mermaid:
        lines.extend(["", "Current problem (flowchart)", "```mermaid", result.problem_flowchart_mermaid, "```"])

    if result.resolution_flowchart_mermaid:
        lines.extend([
            "",
            "How similar issues were resolved (flowchart)",
            "```mermaid",
            result.resolution_flowchart_mermaid,
            "```",
        ])

    if settings.INCLUDE_TICKET_IDS_IN_COMMENT and result.similar_past_tickets:
        lines.extend(["", f"Audit similar tickets: {', '.join(result.similar_past_tickets)}"])

    plain = "\n".join(lines)
    adf = _build_adf(result, header)
    return plain, adf


def _build_adf(result: TicketStatusResponse, header: str) -> Dict[str, Any]:
    content: List[Dict[str, Any]] = [_paragraph(header)]

    if result.rag_resolution_summary:
        content.append(_paragraph(result.rag_resolution_summary))

    if result.problem_flowchart_mermaid:
        content.append(_heading("Current problem (flowchart)"))
        content.append(_code_block(result.problem_flowchart_mermaid, "mermaid"))

    if result.resolution_flowchart_mermaid:
        content.append(_heading("How similar issues were resolved (flowchart)"))
        content.append(_code_block(result.resolution_flowchart_mermaid, "mermaid"))

    settings = get_settings()
    if settings.INCLUDE_TICKET_IDS_IN_COMMENT and result.similar_past_tickets:
        audit = "Audit similar tickets: " + ", ".join(result.similar_past_tickets)
        content.append(_paragraph(audit))

    return {"type": "doc", "version": 1, "content": content}


def _paragraph(text: str) -> Dict[str, Any]:
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}


def _heading(text: str, level: int = 3) -> Dict[str, Any]:
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [{"type": "text", "text": text}],
    }


def _code_block(text: str, language: str = "") -> Dict[str, Any]:
    return {
        "type": "codeBlock",
        "attrs": {"language": language},
        "content": [{"type": "text", "text": text}],
    }
