"""Service logic tests."""

import pytest
from src.services.cache_service import CacheService
from src.api.v1.schemas import TicketStatusResponse


class TestCacheService:
    def test_cache_set_and_get(self):
        cache = CacheService()
        result = TicketStatusResponse(
            ticket_id="TICKET-001",
            assigned_team="Network Support",
            confidence_score=0.95,
            requires_hitl=False,
            status="completed"
        )
        cache.set("TICKET-001", result)
        retrieved = cache.get("TICKET-001")
        assert retrieved is not None
        assert retrieved.ticket_id == "TICKET-001"
