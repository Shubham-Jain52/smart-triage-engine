"""API endpoint definitions."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from typing import Optional
import logging

from src.api.v1.schemas import TriageRequest, TriageResponse, TriageAcceptedResponse
from src.services.triage_service import TriageService
from src.services.cache_service import CacheService

logger = logging.getLogger(__name__)
router = APIRouter()

triage_service = TriageService()
cache_service = CacheService()


@router.post("/triage", response_model=TriageAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_triage(request: TriageRequest, background_tasks: BackgroundTasks):
    """
    Receive raw ticket data and initiate classification.
    
    Returns 202 Accepted immediately.
    Classification happens asynchronously in background.
    """
    logger.info(f"Received triage request for ticket: {request.ticket_id}")
    
    # Add background task for triage processing
    background_tasks.add_task(triage_service.process_triage, request)
    
    return TriageAcceptedResponse(
        ticket_id=request.ticket_id,
        status="processing"
    )


@router.get("/triage/{ticket_id}", response_model=TriageResponse)
async def get_triage_result(ticket_id: str):
    """
    Retrieve the classification result for a ticket.
    
    Returns ticket classification details including:
    - Assigned team
    - Confidence score
    - Whether human review is required
    - Processing status
    """
    logger.info(f"Fetching triage result for ticket: {ticket_id}")
    
    # Check cache first
    cached_result = cache_service.get(ticket_id)
    if cached_result:
        logger.info(f"Cache hit for ticket: {ticket_id}")
        return cached_result
    
    # If not in cache, return processing status or not found
    logger.warning(f"No result found for ticket: {ticket_id}")
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Triage result not found for ticket {ticket_id}. Please check back later."
    )
