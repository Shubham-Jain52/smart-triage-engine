"""Pydantic models for request/response validation."""

from pydantic import BaseModel, Field
from datetime import datetime


class TicketPayload(BaseModel):
    ticket_id: str = Field(..., description="Unique ticket identifier", strict=True)
    title: str = Field(..., description="Ticket title", strict=True)
    description: str = Field(..., description="Ticket description", strict=True)
    created_at: datetime = Field(..., description="Ticket creation timestamp", strict=True)


class TicketStatusResponse(BaseModel):
    ticket_id: str
    assigned_team: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    requires_hitl: bool
    status: str


class TriageAcceptedResponse(BaseModel):
    ticket_id: str
    status: str = "processing"
