"""Core triage service with classification and routing logic."""

import logging

from src.api.v1.schemas import TriageRequest, TriageResponse
from src.models.ml_classifier import MLClassifier
from src.services.cache_service import CacheService
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TriageService:
    def __init__(self):
        self.classifier = MLClassifier()
        self.cache_service = CacheService()
    
    async def process_triage(self, request: TriageRequest) -> TriageResponse:
        logger.info(f"Processing triage for ticket: {request.ticket_id}")
        
        try:
            assigned_team, confidence_score = self.classifier.classify(
                request.title,
                request.description
            )
            
            requires_hitl = confidence_score < settings.CONFIDENCE_THRESHOLD
            
            result = TriageResponse(
                ticket_id=request.ticket_id,
                assigned_team=assigned_team,
                confidence_score=confidence_score,
                requires_hitl=requires_hitl,
                status="completed"
            )
            
            self.cache_service.set(request.ticket_id, result)
            logger.info(f"Triage completed for {request.ticket_id}: team={assigned_team}, confidence={confidence_score:.2f}")
            return result
        
        except Exception as e:
            logger.error(f"Error processing triage for {request.ticket_id}: {e}")
            result = TriageResponse(
                ticket_id=request.ticket_id,
                assigned_team="unassigned",
                confidence_score=0.0,
                requires_hitl=True,
                status="failed"
            )
            self.cache_service.set(request.ticket_id, result)
            return result
