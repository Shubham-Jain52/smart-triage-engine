"""FastAPI dependencies for API routes."""

from typing import Optional

from fastapi import Header, HTTPException, status

from src.config import get_settings


def verify_webhook_ingest_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> None:
    """Require ``X-API-Key`` when ``WEBHOOK_INGEST_API_KEY`` is configured."""
    expected = get_settings().WEBHOOK_INGEST_API_KEY.strip()
    if not expected:
        return
    if not x_api_key or x_api_key.strip() != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )
