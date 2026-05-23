"""Core triage service with classification and routing logic."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from src.api.v1.schemas import TicketPayload, TicketStatusResponse
from src.services.cache_service import CacheService
from src.config import get_settings
from src.models.ml_classifier import MLClassifier

if TYPE_CHECKING:
    from src.services.callback_service import RoutingCallbackService
    from src.services.rag_service import RagService

logger = logging.getLogger(__name__)


class TriageService:
    def __init__(
        self,
        cache_service: Optional[CacheService] = None,
        callback_service: Optional[RoutingCallbackService] = None,
        rag_service: Optional[RagService] = None,
    ):
        self.cache_service = cache_service if cache_service is not None else CacheService()
        self._classifier: Optional[MLClassifier] = None
        self._rag_service = rag_service
        if callback_service is not None:
            self.callback_service = callback_service
        else:
            from src.services.callback_service import RoutingCallbackService as _RoutingCb

            self.callback_service = _RoutingCb()

    @property
    def classifier(self) -> MLClassifier:
        if self._classifier is None:
            self._classifier = MLClassifier()
        return self._classifier

    @property
    def rag_service(self) -> RagService:
        if self._rag_service is None:
            from src.services.rag_service import RagService as _RagService

            self._rag_service = _RagService()
        return self._rag_service

    def process_triage(self, request: TicketPayload) -> TicketStatusResponse:
        logger.info(f"Processing triage for ticket: {request.ticket_id}")

        try:
            assigned_team, confidence_score = self.classifier.classify(
                request.title,
                request.description,
            )

            requires_hitl = confidence_score < get_settings().HITL_THRESHOLD

            rag = self._run_rag_if_enabled(request.title, request.description)

            result = TicketStatusResponse(
                ticket_id=request.ticket_id,
                assigned_team=assigned_team,
                confidence_score=confidence_score,
                requires_hitl=requires_hitl,
                status="completed",
                problem_flowchart_mermaid=rag.problem_flowchart_mermaid,
                resolution_flowchart_mermaid=rag.resolution_flowchart_mermaid,
                rag_resolution_summary=rag.rag_resolution_summary,
                similar_past_tickets=rag.similar_past_tickets,
            )

            self.cache_service.set(request.ticket_id, result)
            logger.info(f"Triage completed for {request.ticket_id}: team={assigned_team}, confidence={confidence_score:.2f}")
            self.callback_service.notify_triage_result(result)
            return result

        except Exception as e:
            logger.exception(f"Error processing triage for {request.ticket_id}: {e}")
            result = TicketStatusResponse(
                ticket_id=request.ticket_id,
                assigned_team="unassigned",
                confidence_score=0.0,
                requires_hitl=True,
                status="failed",
            )
            self.cache_service.set(request.ticket_id, result)
            self.callback_service.notify_triage_result(result)
            return result

    def _run_rag_if_enabled(self, title: str, description: str):
        settings = get_settings()
        if not settings.RAG_ENABLED:
            from src.services.rag_service import RagResult

            return RagResult()
        return self.rag_service.run_rag(title, description)
