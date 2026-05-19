import os
from typing import Optional
from functools import lru_cache


class Settings:
    """Application settings and configuration."""
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Smart Triage Engine"
    PROJECT_VERSION: str = "0.1.0"
    
    # ML Model Configuration
    MODEL_PATH: str = os.getenv("MODEL_PATH", "src/data/pretrained_model.pkl")
    VECTORIZER_PATH: str = os.getenv("VECTORIZER_PATH", "src/data/vectorizer.pkl")
    
    # Confidence Threshold for HITL (Human-In-The-Loop)
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.80"))
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Cache Configuration
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
