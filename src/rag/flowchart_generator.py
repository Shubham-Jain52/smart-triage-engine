"""Mermaid flowchart generation via BYOK LLM."""

from __future__ import annotations

import logging
import re
from typing import List, Optional, TYPE_CHECKING

from src.config import get_settings
from src.integrations.llm.client import LLMClient

if TYPE_CHECKING:
    from src.rag.retriever import RetrievalContext

logger = logging.getLogger(__name__)

_FLOWCHART_HEADER = re.compile(r"^\s*flowchart\s+(TD|LR)\b", re.IGNORECASE | re.MULTILINE)
_CODE_BLOCK = re.compile(r"```(?:mermaid)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


class FlowchartGenerator:
    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self._llm = llm_client

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm

    def generate_problem_flowchart(self, title: str, description: str) -> str:
        settings = get_settings()
        system = (
            "You output valid Mermaid flowchart syntax only. "
            f"Use flowchart TD or flowchart LR. Maximum {settings.FLOWCHART_MAX_NODES} nodes. "
            "No markdown fences, no explanation, no ticket IDs in node labels."
        )
        user = (
            f"Create a problem-structure flowchart for this IT ticket.\n"
            f"Title: {title}\nDescription: {description}\n"
            "Show symptoms, decision branches, and likely components to check."
        )
        return self._generate_with_retry(system, user)

    def generate_resolution_flowchart(
        self,
        title: str,
        description: str,
        contexts: List[RetrievalContext],
    ) -> str:
        settings = get_settings()
        history = self._format_contexts(contexts)
        system = (
            "You output valid Mermaid flowchart syntax only. "
            f"Use flowchart TD or flowchart LR. Maximum {settings.FLOWCHART_MAX_NODES} nodes. "
            "Merge similar past fixes into one resolution path. "
            "Do not put Jira ticket IDs in node labels; use generic step names."
        )
        if not contexts:
            user = (
                f"No similar resolved tickets were found.\n"
                f"Current ticket — Title: {title}\nDescription: {description}\n"
                "Create a generic troubleshooting/resolution flowchart for this type of issue."
            )
        else:
            user = (
                f"Current ticket — Title: {title}\nDescription: {description}\n\n"
                f"Similar past resolutions:\n{history}\n\n"
                "Create one flowchart showing how similar issues were typically fixed."
            )
        return self._generate_with_retry(system, user)

    def _generate_with_retry(self, system: str, user: str) -> str:
        settings = get_settings()
        last_error = ""
        attempts = max(1, settings.FLOWCHART_LLM_RETRIES + 1)
        prompt_user = user
        for attempt in range(1, attempts + 1):
            raw = self.llm.chat(system, prompt_user)
            mermaid = extract_mermaid(raw)
            if validate_mermaid(mermaid, settings.FLOWCHART_MAX_NODES):
                return mermaid
            last_error = f"invalid mermaid on attempt {attempt}"
            logger.warning("Flowchart validation failed (attempt %s)", attempt)
            prompt_user = user + "\n\nReturn ONLY valid Mermaid flowchart code starting with flowchart TD or flowchart LR."
        raise ValueError(f"Failed to generate valid Mermaid flowchart: {last_error}")

    @staticmethod
    def _format_contexts(contexts: List[RetrievalContext]) -> str:
        blocks: List[str] = []
        for i, ctx in enumerate(contexts, start=1):
            blocks.append(
                f"--- Match {i} (score={ctx.score:.2f}) ---\n"
                f"Problem: {ctx.title}\n{ctx.description}\n"
                f"Resolution: {ctx.resolution_text}\n"
                f"Team: {ctx.team}"
            )
        return "\n\n".join(blocks)


def extract_mermaid(raw: str) -> str:
    """Strip markdown fences and whitespace from LLM output."""
    text = raw.strip()
    match = _CODE_BLOCK.search(text)
    if match:
        text = match.group(1).strip()
    return text.strip()


def validate_mermaid(text: str, max_nodes: int) -> bool:
    """Lightweight Mermaid syntax check."""
    if not text or not _FLOWCHART_HEADER.search(text):
        return False
    node_count = text.count("[") + text.count("(") + text.count("{")
    return node_count <= max_nodes + 5
