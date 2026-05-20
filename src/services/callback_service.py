"""Outbound HTTP callback to the ticketing platform after triage completes."""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from src.api.v1.schemas import TicketStatusResponse
from src.config import get_settings

logger = logging.getLogger(__name__)


class RoutingCallbackService:
    """POST triage results to ``TRIAGE_CALLBACK_URL`` when configured."""

    def notify_triage_result(self, result: TicketStatusResponse) -> None:
        settings = get_settings()
        url = settings.TRIAGE_CALLBACK_URL.strip()
        if not url:
            return

        payload = result.model_dump(mode="json")
        headers: dict[str, str] = {"Content-Type": "application/json"}
        api_key = settings.TRIAGE_CALLBACK_API_KEY.strip()
        if api_key:
            headers["X-API-Key"] = api_key

        timeout = float(settings.TRIAGE_CALLBACK_TIMEOUT_SECONDS)
        max_attempts = settings.TRIAGE_CALLBACK_RETRIES + 1

        last_error: Optional[BaseException] = None
        with httpx.Client(timeout=timeout) as client:
            for attempt in range(1, max_attempts + 1):
                try:
                    response = client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    logger.info(
                        "Routing callback succeeded for ticket_id=%s (attempt %s)",
                        result.ticket_id,
                        attempt,
                    )
                    return
                except Exception as exc:
                    last_error = exc
                    logger.warning(
                        "Routing callback attempt %s/%s failed for ticket_id=%s: %s",
                        attempt,
                        max_attempts,
                        result.ticket_id,
                        exc,
                    )

        logger.error(
            "Routing callback exhausted retries for ticket_id=%s: %s",
            result.ticket_id,
            last_error,
        )
