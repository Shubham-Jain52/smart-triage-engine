"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from src.config import get_settings
from src.api.v1 import routes

logger = logging.getLogger(__name__)
settings = get_settings()

logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

app = FastAPI(title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION, description="Smart Triage Engine")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(routes.router, prefix=settings.API_V1_STR, tags=["triage"])


@app.get("/")
async def root():
    return {"message": "Smart Triage Engine API", "version": settings.PROJECT_VERSION}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
