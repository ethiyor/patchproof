from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.github_webhook import router as github_webhook_router
from backend.api.health import router as health_router
from backend.api.reviews import router as reviews_router
from backend.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Code before ``yield`` runs on startup.
    Code after ``yield`` runs on shutdown.

    Phase 4.1: nothing to initialise yet - the database connection pool
    will be set up here in milestone 4.2.
    """
    settings = get_settings()
    logger.info(
        "PatchProof API starting | debug=%s | db=%s | dashboard=%s",
        settings.debug,
        "configured" if settings.database_url else "not configured",
        "enabled" if settings.serve_dashboard else "disabled",
    )
    yield
    logger.info("PatchProof API shutting down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

settings = get_settings()

app = FastAPI(
    title="PatchProof API",
    description="Spec-to-merge verification for AI-generated code changes.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(reviews_router)
app.include_router(github_webhook_router)

frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if settings.serve_dashboard and frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
