import os
from functools import lru_cache


class Settings:
    """Application settings and configuration."""
    
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Smart Triage Engine"
    PROJECT_VERSION: str = "0.1.0"
    MODEL_PATH: str = os.getenv("MODEL_PATH", "src/data/pretrained_model.pkl")
    VECTORIZER_PATH: str = os.getenv("VECTORIZER_PATH", "src/data/vectorizer.pkl")
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.80"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
