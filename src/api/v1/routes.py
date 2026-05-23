"""API endpoint definitions."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
import logging

from src.api.v1.schemas import (
    TicketPayload,
    TicketStatusResponse,
    TriageAcceptedResponse,
    ResolvedIngestPayload,
    ResolvedIngestResponse,
)
from src.api.v1.deps import verify_webhook_ingest_key
from src.services.triage_service import TriageService
from src.services.cache_service import CacheService
from src.services.resolve_ingest_service import ResolveIngestService

logger = logging.getLogger(__name__)
router = APIRouter()

cache_service = CacheService()
triage_service = TriageService(cache_service=cache_service)
resolve_ingest_service = ResolveIngestService()


@router.post(
    "/triage",
    response_model=TriageAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_webhook_ingest_key)],
)
async def create_triage(request: TicketPayload, background_tasks: BackgroundTasks):
    logger.info(f"Received triage request for ticket: {request.ticket_id}")

    existing = cache_service.get(request.ticket_id)
    if existing is not None and existing.status in ("completed", "failed"):
        return TriageAcceptedResponse(ticket_id=request.ticket_id, status=existing.status)
    if existing is not None and existing.status == "processing":
        return TriageAcceptedResponse(ticket_id=request.ticket_id, status="processing")

    processing_result = TicketStatusResponse(
        ticket_id=request.ticket_id,
        assigned_team="pending",
        confidence_score=0.0,
        requires_hitl=False,
        status="processing",
    )
    cache_service.set(request.ticket_id, processing_result)

    background_tasks.add_task(triage_service.process_triage, request)
    return TriageAcceptedResponse(ticket_id=request.ticket_id, status="processing")


@router.get("/triage/{ticket_id}", response_model=TicketStatusResponse)
async def get_triage_result(ticket_id: str):
    logger.info(f"Fetching triage result for ticket: {ticket_id}")
    cached_result = cache_service.get(ticket_id)
    if cached_result:
        return cached_result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Triage result not found for ticket {ticket_id}")


@router.post(
    "/ingest/resolved",
    response_model=ResolvedIngestResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_webhook_ingest_key)],
)
async def ingest_resolved_ticket(request: ResolvedIngestPayload):
    """Upsert a resolved Jira issue into Pinecone (Phase 3.1 on-resolve re-ingest)."""
    logger.info("On-resolve ingest requested for ticket: %s", request.ticket_id)
    result = resolve_ingest_service.ingest_resolved_ticket(request.ticket_id)
    return ResolvedIngestResponse(
        ticket_id=result.ticket_id,
        status=result.status,
        message=result.message,
    )
