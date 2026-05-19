"""In-memory cache service for classification results."""

import logging
import threading
from datetime import datetime, timedelta

from src.api.v1.schemas import TicketStatusResponse
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheService:
    def __init__(self):
        self._cache = {}
        self._lock = threading.RLock()
    
    def get(self, ticket_id: str):
        with self._lock:
            if not settings.CACHE_ENABLED or ticket_id not in self._cache:
                return None
            
            result, timestamp = self._cache[ticket_id]
            if datetime.now() - timestamp > timedelta(seconds=settings.CACHE_TTL_SECONDS):
                del self._cache[ticket_id]
                return None
            
            return result
    
    def set(self, ticket_id: str, result: TicketStatusResponse):
        with self._lock:
            if settings.CACHE_ENABLED:
                self._cache[ticket_id] = (result, datetime.now())
    
    def delete(self, ticket_id: str):
        with self._lock:
            if ticket_id in self._cache:
                del self._cache[ticket_id]
    
    def clear(self):
        with self._lock:
            self._cache.clear()
