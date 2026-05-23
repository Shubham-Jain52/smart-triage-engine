"""Short RAG caption for triage output."""

from __future__ import annotations

import logging
from typing import List, Optional, TYPE_CHECKING

from src.integrations.llm.client import LLMClient

if TYPE_CHECKING:
    from src.rag.retriever import RetrievalContext

logger = logging.getLogger(__name__)


class ResolutionSummaryGenerator:
    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self._llm = llm_client

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm

    def generate_summary(
        self,
        title: str,
        description: str,
        contexts: List[RetrievalContext],
    ) -> str:
        if not contexts:
            return "No similar resolved tickets found; use the problem flowchart to structure investigation."

        system = (
            "Write 1-2 sentences summarizing how similar past tickets were resolved. "
            "Plain text only, no markdown, no ticket IDs."
        )
        history_lines = []
        for ctx in contexts[:3]:
            history_lines.append(f"- {ctx.title}: {ctx.resolution_text[:300]}")
        user = (
            f"Current ticket: {title}\n{description}\n\n"
            f"Past fixes:\n" + "\n".join(history_lines)
        )
        try:
            return self.llm.chat(system, user).strip()
        except Exception as e:
            logger.warning("Resolution summary generation failed: %s", e)
            return f"Found {len(contexts)} similar past ticket(s) with relevant resolution patterns."
