from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from backend.api.health import router as health_router
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

    Phase 4.1: nothing to initialise yet — the database connection pool
    will be set up here in milestone 4.2.
    """
    settings = get_settings()
    logger.info(
        "PatchProof API starting | debug=%s | db=%s",
        settings.debug,
        "configured" if settings.database_url else "not configured",
    )
    yield
    logger.info("PatchProof API shutting down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="PatchProof API",
    description="Spec-to-merge verification for AI-generated code changes.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
