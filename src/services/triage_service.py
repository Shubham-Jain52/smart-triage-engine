"""Core triage service with classification and routing logic."""

import logging
from datetime import datetime

from src.api.v1.schemas import TriageRequest, TriageResponse
from src.models.ml_classifier import MLClassifier
from src.services.cache_service import CacheService
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TriageService:
    """Handles triage logic, classification, and result caching."""
    
    def __init__(self):
        """Initialize service with classifier and cache."""
        self.classifier = MLClassifier()
        self.cache_service = CacheService()
    
    async def process_triage(self, request: TriageRequest) -> TriageResponse:
        """
        Process triage for a ticket.
        
        Steps:
        1. Classify ticket using ML model
        2. Determine if HITL (Human-In-The-Loop) is needed
        3. Cache the result
        4. Return classification result
        """
        logger.info(f"Processing triage for ticket: {request.ticket_id}")
        
        try:
            # Classify using ML model
            assigned_team, confidence_score = self.classifier.classify(
                request.title,
                request.description
            )
            
            # Determine if HITL is needed (confidence < threshold)
            requires_hitl = confidence_score < settings.CONFIDENCE_THRESHOLD
            
            # Create response
            result = TriageResponse(
                ticket_id=request.ticket_id,
                assigned_team=assigned_team,
                confidence_score=confidence_score,
                requires_hitl=requires_hitl,
                status="completed"
            )
            
            # Cache the result
            self.cache_service.set(request.ticket_id, result)
            
            logger.info(
                f"Triage completed for {request.ticket_id}: "
                f"team={assigned_team}, confidence={confidence_score:.2f}, "
                f"hitl={requires_hitl}"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error processing triage for {request.ticket_id}: {e}")
            
            # Create failed response
            result = TriageResponse(
                ticket_id=request.ticket_id,
                assigned_team="unassigned",
                confidence_score=0.0,
                requires_hitl=True,
                status="failed"
            )
            
            self.cache_service.set(request.ticket_id, result)
            return result
