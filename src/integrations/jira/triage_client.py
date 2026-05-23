"""HTTP client for the triage API (Phase 3 worker)."""

from __future__ import annotations

import logging
import time
from typing import Optional

import httpx

from src.api.v1.schemas import TicketPayload, TicketStatusResponse
from src.config import get_settings

logger = logging.getLogger(__name__)


class TriageApiClient:
    """POST triage + poll GET until terminal status."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.TRIAGE_API_URL).rstrip("/")
        self.api_v1 = f"{self.base_url}{settings.API_V1_STR}"
        self.api_key = (api_key if api_key is not None else settings.WEBHOOK_INGEST_API_KEY).strip()
        self.poll_interval = settings.TRIAGE_POLL_INTERVAL_SECONDS
        self.max_attempts = settings.TRIAGE_POLL_MAX_ATTEMPTS
        self.timeout = settings.TRIAGE_POLL_TIMEOUT_SECONDS

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def submit_triage(self, payload: TicketPayload) -> None:
        url = f"{self.api_v1}/triage"
        body = payload.model_dump(mode="json")
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(url, json=body, headers=self._headers())
            r.raise_for_status()
        logger.info("Submitted triage for %s", payload.ticket_id)

    def get_result(self, ticket_id: str) -> TicketStatusResponse:
        url = f"{self.api_v1}/triage/{ticket_id}"
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(url, headers=self._headers())
            r.raise_for_status()
            return TicketStatusResponse.model_validate(r.json())

    def submit_and_wait(self, payload: TicketPayload) -> TicketStatusResponse:
        self.submit_triage(payload)
        for attempt in range(1, self.max_attempts + 1):
            result = self.get_result(payload.ticket_id)
            if result.status in ("completed", "failed"):
                return result
            logger.debug(
                "Triage still processing for %s (attempt %s/%s)",
                payload.ticket_id,
                attempt,
                self.max_attempts,
            )
            time.sleep(self.poll_interval)
        raise TimeoutError(
            f"Triage for {payload.ticket_id} did not complete after {self.max_attempts} attempts"
        )
