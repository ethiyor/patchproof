from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.services.github_webhook_processor import (
    parse_pull_request_webhook,
    process_pull_request_webhook,
)
from backend.services.webhook_verifier import verify_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["github"])


@router.post("/webhook")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Annotated[str | None, Header()] = None,
    x_github_event: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    """Receive GitHub webhooks after validating the raw payload signature."""
    payload = await request.body()
    secret = get_settings().github_webhook_secret
    if not secret:
        logger.error("GitHub webhook received but GITHUB_WEBHOOK_SECRET is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub webhook secret is not configured.",
        )

    if not verify_signature(payload, x_hub_signature_256, secret):
        logger.warning("Rejected GitHub webhook with missing or invalid signature.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid GitHub webhook signature.",
        )

    if x_github_event != "pull_request":
        logger.info("Ignored GitHub webhook event: %s", x_github_event or "missing")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ignored", "event": x_github_event},
        )

    try:
        parsed_payload = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GitHub webhook JSON payload.",
        ) from exc

    try:
        event = parse_pull_request_webhook(parsed_payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    background_tasks.add_task(process_pull_request_webhook, event)
    logger.info(
        "Accepted GitHub pull_request webhook: repo=%s pr=%s action=%s",
        event.repo_full_name,
        event.pr_number,
        event.action or "unknown",
    )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"status": "accepted"},
    )