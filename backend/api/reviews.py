from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.db.models import ChangedFile, Review
from backend.db.session import get_db_session
from backend.schemas.review_schemas import LocalReviewRequest, ReviewResponse
from core.diff_parser import parse_diff
from core.report_generator import generate_full_report, generate_report
from core.risk_scorer import compute_risk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reviews", tags=["reviews"])


# ---------------------------------------------------------------------------
# POST /reviews/local
# ---------------------------------------------------------------------------

@router.post("/local", response_model=ReviewResponse)
async def create_local_review(
    body: LocalReviewRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ReviewResponse:
    """
    Analyze a local git diff against a task description.

    Runs the diff parser and risk scorer. If OPENAI_API_KEY is configured,
    runs the full 5-step LLM pipeline. Persists the review to the database
    and returns the structured report.
    """
    settings = get_settings()

    # ── 1. Parse diff + compute rule-based risk ───────────────────────────────
    parsed = parse_diff(body.diff)
    risk = compute_risk(parsed)
    logger.info(
        "Review started: repo=%s risk=%s files=%d",
        body.repo_name, risk.level, parsed.total_files,
    )

    # ── 2. Run LLM pipeline or fall back to basic report ─────────────────────
    if settings.openai_api_key:
        from llm.pipeline import run_pipeline
        pipeline_result = run_pipeline(
            task_text=body.task,
            diff_text=body.diff,
            parsed_diff=parsed,
            risk=risk,
        )
        report_md = generate_full_report(
            diff=parsed,
            risk=risk,
            task_text=body.task,
            repo_name=body.repo_name,
            branch=body.branch,
            pipeline_result=pipeline_result,
        )
        merge_rec = pipeline_result.report_sections.merge_recommendation
    else:
        report_md = generate_report(
            diff=parsed,
            risk=risk,
            task_text=body.task,
            repo_name=body.repo_name,
            branch=body.branch,
        )
        merge_rec = "needs_changes" if risk.score >= 3 else "ready"

    # ── 3. Persist to database ────────────────────────────────────────────────
    review = Review(
        task_text=body.task,
        diff_text=body.diff[:50_000],   # cap at 50k chars to avoid huge rows
        risk_score=risk.score,
        risk_level=risk.level,
        merge_recommendation=merge_rec,
        report_markdown=report_md,
    )
    db.add(review)
    await db.flush()    # assign review.id without committing yet

    for f in parsed.files:
        db.add(ChangedFile(
            review_id=review.id,
            file_path=f.path,
            status=f.status,
            language=f.language,
            additions=f.additions,
            deletions=f.deletions,
            risk_flags=f.risk_flags if f.risk_flags else None,
        ))

    await db.commit()
    logger.info("Review saved: id=%s recommendation=%s", review.id, merge_rec)

    # ── 4. Return response ────────────────────────────────────────────────────
    return ReviewResponse(
        review_id=str(review.id),
        status="completed",
        report_markdown=report_md,
        risk_score=risk.score,
        risk_level=risk.level,
        merge_recommendation=merge_rec,
    )
