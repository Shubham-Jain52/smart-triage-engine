"""Pydantic models for request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TriageRequest(BaseModel):
    """Request schema for POST /api/v1/triage endpoint."""
    
    ticket_id: str = Field(..., description="Unique ticket identifier")
    title: str = Field(..., description="Ticket title")
    description: str = Field(..., description="Ticket description")
    created_at: datetime = Field(..., description="Ticket creation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": "TICKET-001",
                "title": "Network connectivity issue",
                "description": "Unable to connect to corporate VPN",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }


class TriageResponse(BaseModel):
    """Response schema for triage classification."""
    
    ticket_id: str = Field(..., description="Ticket identifier")
    assigned_team: str = Field(..., description="Assigned team name")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    requires_hitl: bool = Field(..., description="Whether human review is required")
    status: str = Field(..., description="Processing status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": "TICKET-001",
                "assigned_team": "Network Support",
                "confidence_score": 0.92,
                "requires_hitl": False,
                "status": "completed"
            }
        }


class TriageAcceptedResponse(BaseModel):
    """Response schema for immediate 202 Accepted response."""
    
    ticket_id: str = Field(..., description="Ticket identifier")
    status: str = Field(default="processing", description="Processing status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": "TICKET-001",
                "status": "processing"
            }
        }
