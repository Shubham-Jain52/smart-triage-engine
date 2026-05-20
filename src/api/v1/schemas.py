"""Pydantic models for request/response validation."""

from pydantic import BaseModel, Field
from datetime import datetime


class TicketPayload(BaseModel):
    ticket_id: str = Field(..., description="Unique ticket identifier")
    title: str = Field(..., description="Ticket title")
    description: str = Field(..., description="Ticket description")
    created_at: datetime = Field(..., description="Ticket creation timestamp")


class TicketStatusResponse(BaseModel):
    ticket_id: str
    assigned_team: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    requires_hitl: bool
    status: str


class TriageAcceptedResponse(BaseModel):
    ticket_id: str
    status: str = "processing"
