"""API endpoint definitions."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
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
    logger.info(f"Received triage request for ticket: {request.ticket_id}")
    background_tasks.add_task(triage_service.process_triage, request)
    return TriageAcceptedResponse(ticket_id=request.ticket_id, status="processing")


@router.get("/triage/{ticket_id}", response_model=TriageResponse)
async def get_triage_result(ticket_id: str):
    logger.info(f"Fetching triage result for ticket: {ticket_id}")
    cached_result = cache_service.get(ticket_id)
    if cached_result:
        return cached_result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Triage result not found for ticket {ticket_id}")
