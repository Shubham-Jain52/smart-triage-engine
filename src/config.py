import os
from functools import lru_cache
from typing import List


class Settings:
    """Application settings loaded from the environment (fresh values per instance)."""

    def __init__(self) -> None:
        self.API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")
        self.PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Smart Triage Engine")
        self.PROJECT_VERSION: str = os.getenv("PROJECT_VERSION", "0.1.0")
        self.MODEL_PATH: str = os.getenv("MODEL_PATH", "src/data/pretrained_model.pkl")
        self.VECTORIZER_PATH: str = os.getenv("VECTORIZER_PATH", "src/data/vectorizer.pkl")
        self.CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.80"))
        self.HITL_THRESHOLD: float = float(os.getenv("HITL_THRESHOLD", "0.80"))
        self.CANDIDATE_LABELS: List[str] = [
            s.strip() for s in os.getenv("CANDIDATE_LABELS", "IT Support,DevOps,HR,Security,Hardware").split(",")
        ]
        self.ZS_MODEL_NAME: str = os.getenv("ZS_MODEL_NAME", "valhalla/distilbart-mnli-12-1")
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
        self.CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
        self.MOCK_PROCESSING_DELAY_SECONDS: int = int(os.getenv("MOCK_PROCESSING_DELAY_SECONDS", "2"))

        self.TRIAGE_CALLBACK_URL: str = os.getenv("TRIAGE_CALLBACK_URL", "").strip()
        self.TRIAGE_CALLBACK_API_KEY: str = os.getenv("TRIAGE_CALLBACK_API_KEY", "").strip()
        self.TRIAGE_CALLBACK_TIMEOUT_SECONDS: float = float(os.getenv("TRIAGE_CALLBACK_TIMEOUT_SECONDS", "5.0"))
        self.TRIAGE_CALLBACK_RETRIES: int = int(os.getenv("TRIAGE_CALLBACK_RETRIES", "2"))

        self.WEBHOOK_INGEST_API_KEY: str = os.getenv("WEBHOOK_INGEST_API_KEY", "").strip()


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
