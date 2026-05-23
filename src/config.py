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

        # Phase 2 / 5 — RAG & Pinecone (BYOK)
        self.RAG_ENABLED: bool = os.getenv("RAG_ENABLED", "false").lower() == "true"
        self.PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "").strip()
        self.PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "ticket-routing").strip()
        self.PINECONE_NAMESPACE: str = os.getenv("PINECONE_NAMESPACE", "").strip()
        self.PINECONE_CLOUD: str = os.getenv("PINECONE_CLOUD", "aws").strip()
        self.PINECONE_REGION: str = os.getenv("PINECONE_REGION", "us-east-1").strip()
        self.EMBEDDING_MODEL_NAME: str = os.getenv(
            "EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"
        ).strip()
        self.RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "3"))

        # Phase 2 — LLM flowchart generation (BYOK)
        self.LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
        self.OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip().rstrip("/")
        self.OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2").strip()
        self.OLLAMA_TIMEOUT_SECONDS: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
        self.OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        self.OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
        self.FLOWCHART_MAX_NODES: int = int(os.getenv("FLOWCHART_MAX_NODES", "15"))
        self.FLOWCHART_LLM_RETRIES: int = int(os.getenv("FLOWCHART_LLM_RETRIES", "1"))

        # Phase 5 — Jira historical ingest
        self.JIRA_BASE_URL: str = os.getenv("JIRA_BASE_URL", "").strip().rstrip("/")
        self.JIRA_EMAIL: str = os.getenv("JIRA_EMAIL", "").strip()
        self.JIRA_API_TOKEN: str = os.getenv("JIRA_API_TOKEN", "").strip()
        self.JIRA_PROJECT_KEY: str = os.getenv("JIRA_PROJECT_KEY", "").strip()
        self.INGEST_MONTHS: int = int(os.getenv("INGEST_MONTHS", "12"))
        self.INGEST_JQL: str = os.getenv("INGEST_JQL", "").strip()
        self.INGEST_BATCH_SIZE: int = int(os.getenv("INGEST_BATCH_SIZE", "100"))
        self.INGEST_MAX_ISSUES: int = int(os.getenv("INGEST_MAX_ISSUES", "0"))  # 0 = no limit
        self.INGEST_SOURCE: str = os.getenv("INGEST_SOURCE", "dummy").strip().lower()
        self.INGEST_CSV_PATH: str = os.getenv("INGEST_CSV_PATH", "").strip()

        # Phase 3.1 — on-resolve continuous re-ingest
        self.INGEST_ON_RESOLVE_ENABLED: bool = (
            os.getenv("INGEST_ON_RESOLVE_ENABLED", "false").lower() == "true"
        )
        self.INGEST_ON_RESOLVE_REQUIRE_RESOLUTION: bool = (
            os.getenv("INGEST_ON_RESOLVE_REQUIRE_RESOLUTION", "true").lower() == "true"
        )
        self.INGEST_ON_RESOLVE_POLL_MINUTES: int = int(
            os.getenv("INGEST_ON_RESOLVE_POLL_MINUTES", "15")
        )
        self.INGEST_ON_RESOLVE_POLL_INTERVAL_SECONDS: int = int(
            os.getenv("INGEST_ON_RESOLVE_POLL_INTERVAL_SECONDS", "300")
        )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
