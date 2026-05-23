"""Orchestrate retrieval + flowchart generation for Phase 2 RAG."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from src.config import get_settings
from src.rag.flowchart_generator import FlowchartGenerator
from src.rag.resolution_generator import ResolutionSummaryGenerator
from src.rag.retriever import TicketRetriever

logger = logging.getLogger(__name__)


@dataclass
class RagResult:
    problem_flowchart_mermaid: str = ""
    resolution_flowchart_mermaid: str = ""
    rag_resolution_summary: str = ""
    similar_past_tickets: List[str] = field(default_factory=list)


class RagService:
    def __init__(
        self,
        retriever: Optional[TicketRetriever] = None,
        flowchart_generator: Optional[FlowchartGenerator] = None,
        summary_generator: Optional[ResolutionSummaryGenerator] = None,
    ) -> None:
        self._retriever = retriever
        self._flowchart_generator = flowchart_generator
        self._summary_generator = summary_generator

    @property
    def retriever(self) -> TicketRetriever:
        if self._retriever is None:
            self._retriever = TicketRetriever()
        return self._retriever

    @property
    def flowchart_generator(self) -> FlowchartGenerator:
        if self._flowchart_generator is None:
            self._flowchart_generator = FlowchartGenerator()
        return self._flowchart_generator

    @property
    def summary_generator(self) -> ResolutionSummaryGenerator:
        if self._summary_generator is None:
            self._summary_generator = ResolutionSummaryGenerator()
        return self._summary_generator

    def run_rag(self, title: str, description: str) -> RagResult:
        settings = get_settings()
        if not settings.RAG_ENABLED:
            return RagResult()
        if not settings.PINECONE_API_KEY:
            logger.warning("RAG_ENABLED but PINECONE_API_KEY is missing; skipping RAG")
            return RagResult()

        try:
            retrieval = self.retriever.retrieve(title, description)
            problem = self.flowchart_generator.generate_problem_flowchart(title, description)
            resolution = self.flowchart_generator.generate_resolution_flowchart(
                title, description, retrieval.contexts
            )
            summary = self.summary_generator.generate_summary(
                title, description, retrieval.contexts
            )
            return RagResult(
                problem_flowchart_mermaid=problem,
                resolution_flowchart_mermaid=resolution,
                rag_resolution_summary=summary,
                similar_past_tickets=retrieval.similar_past_tickets,
            )
        except Exception as e:
            logger.warning("RAG pipeline failed: %s", e, exc_info=True)
            return RagResult()
