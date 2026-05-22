"""Extract plain text from Jira description HTML and Atlassian Document Format."""

from __future__ import annotations

import re
from typing import Any, List


def strip_html(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return " ".join(cleaned.split())


def adf_to_text(node: Any) -> str:
    """Best-effort plain text from Jira ADF JSON."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return " ".join(adf_to_text(item) for item in node).strip()
    if not isinstance(node, dict):
        return str(node)

    parts: List[str] = []
    if node.get("type") == "text" and "text" in node:
        parts.append(str(node["text"]))

    for key in ("content", "paragraph", "bulletList", "orderedList", "listItem"):
        child = node.get(key)
        if child is not None:
            parts.append(adf_to_text(child))

    return " ".join(p for p in parts if p).strip()


def jira_description_to_text(description: Any) -> str:
    """Normalize Jira description field (string, ADF dict, or None)."""
    if description is None:
        return ""
    if isinstance(description, str):
        return strip_html(description)
    if isinstance(description, dict):
        return adf_to_text(description)
    return strip_html(str(description))
