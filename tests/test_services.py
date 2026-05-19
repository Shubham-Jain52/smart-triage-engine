"""Service logic tests."""

import pytest
from src.services.cache_service import CacheService
from src.api.v1.schemas import TriageResponse


class TestCacheService:
    """Test cache service."""
    
    def test_cache_set_and_get(self):
        """Test setting and retrieving from cache."""
        cache = CacheService()
        
        result = TriageResponse(
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
        assert retrieved.assigned_team == "Network Support"
    
    def test_cache_delete(self):
        """Test deleting from cache."""
        cache = CacheService()
        
        result = TriageResponse(
            ticket_id="TICKET-002",
            assigned_team="Security",
            confidence_score=0.88,
            requires_hitl=False,
            status="completed"
        )
        
        cache.set("TICKET-002", result)
        cache.delete("TICKET-002")
        
        assert cache.get("TICKET-002") is None
