"""In-memory cache service for classification results."""

import logging
from typing import Optional, Dict
from datetime import datetime, timedelta

from src.api.v1.schemas import TriageResponse
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheService:
    """In-memory cache for triage results."""
    
    def __init__(self):
        """Initialize cache."""
        self._cache: Dict[str, tuple] = {}  # {ticket_id: (result, timestamp)}
    
    def get(self, ticket_id: str) -> Optional[TriageResponse]:
        """
        Retrieve cached result for a ticket.
        
        Returns None if not found or expired.
        """
        if not settings.CACHE_ENABLED:
            return None
        
        if ticket_id not in self._cache:
            return None
        
        result, timestamp = self._cache[ticket_id]
        
        # Check if expired
        if datetime.now() - timestamp > timedelta(seconds=settings.CACHE_TTL_SECONDS):
            del self._cache[ticket_id]
            logger.debug(f"Cache expired for ticket: {ticket_id}")
            return None
        
        logger.debug(f"Cache hit for ticket: {ticket_id}")
        return result
    
    def set(self, ticket_id: str, result: TriageResponse):
        """Store result in cache."""
        if not settings.CACHE_ENABLED:
            return
        
        self._cache[ticket_id] = (result, datetime.now())
        logger.debug(f"Cached result for ticket: {ticket_id}")
    
    def delete(self, ticket_id: str):
        """Delete result from cache."""
        if ticket_id in self._cache:
            del self._cache[ticket_id]
            logger.debug(f"Deleted cache for ticket: {ticket_id}")
    
    def clear(self):
        """Clear entire cache."""
        self._cache.clear()
        logger.debug("Cache cleared")
