from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import get_settings
from backend.db.models import ChangedFile, PullRequest, Repository, Review
from backend.db.session import get_db_session
from backend.services.pr_commenter import PRCommentError, post_review_comment
from backend.schemas.review_schemas import (
    ChangedFileResponse,
    GithubPRReviewRequest,
    LocalReviewRequest,
    RequirementCheckResponse,
    ReviewCommentResponse,
    ReviewDetailResponse,
    ReviewFindingResponse,
    ReviewResponse,
)
from cli.github_client import GitHubClient, parse_pr_url
from core.diff_parser import parse_diff
from core.report_generator import generate_full_report, generate_report
from core.risk_scorer import compute_risk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reviews", tags=["reviews"])


# ---------------------------------------------------------------------------
# Shared review engine
# ---------------------------------------------------------------------------

async def _analyze_and_save_review(
    *,
    db: AsyncSession,
    task_text: str,
    raw_diff: str,
    repo_name: str,
    branch: str,
    repository_id: uuid.UUID | None = None,
    pull_request_id: uuid.UUID | None = None,
) -> ReviewResponse:
    settings = get_settings()

    parsed = parse_diff(raw_diff)
    risk = compute_risk(parsed)
    logger.info(
        "Review started: repo=%s risk=%s files=%d",
        repo_name, risk.level, parsed.total_files,
    )

    if settings.openai_api_key:
        from llm.pipeline import run_pipeline
        pipeline_result = run_pipeline(
            task_text=task_text,
            diff_text=raw_diff,
            parsed_diff=parsed,
            risk=risk,
        )
        report_md = generate_full_report(
            diff=parsed,
            risk=risk,
            task_text=task_text,
            repo_name=repo_name,
            branch=branch,
            pipeline_result=pipeline_result,
        )
        merge_rec = pipeline_result.report_sections.merge_recommendation
    else:
        report_md = generate_report(
            diff=parsed,
            risk=risk,
            task_text=task_text,
            repo_name=repo_name,
            branch=branch,
        )
        merge_rec = "needs_changes" if risk.score >= 3 else "ready"

    review = Review(
        id=uuid.uuid4(),
        repository_id=repository_id,
        pull_request_id=pull_request_id,
        task_text=task_text,
        diff_text=raw_diff[:50_000],
        risk_score=risk.score,
        risk_level=risk.level,
        merge_recommendation=merge_rec,
        report_markdown=report_md,
    )
    db.add(review)
    await db.flush()

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

    return ReviewResponse(
        review_id=str(review.id),
        status="completed",
        report_markdown=report_md,
        risk_score=risk.score,
        risk_level=risk.level,
        merge_recommendation=merge_rec,
    )


async def _get_or_create_repository(
    db: AsyncSession,
    *,
    owner: str,
    name: str,
) -> Repository:
    result = await db.execute(
        select(Repository).where(
            Repository.owner == owner,
            Repository.name == name,
            Repository.provider == "github",
        )
    )
    repository = result.scalar_one_or_none()
    if repository:
        return repository

    repository = Repository(
        id=uuid.uuid4(),
        owner=owner,
        name=name,
        provider="github",
    )
    db.add(repository)
    await db.flush()
    return repository


async def _get_or_create_pull_request(
    db: AsyncSession,
    *,
    repository: Repository,
    pr_number: int,
    title: str,
    author: str,
    base_branch: str,
    head_branch: str,
    state: str,
) -> PullRequest:
    result = await db.execute(
        select(PullRequest).where(
            PullRequest.repository_id == repository.id,
            PullRequest.pr_number == pr_number,
        )
    )
    pull_request = result.scalar_one_or_none()
    if pull_request:
        pull_request.title = title
        pull_request.author = author
        pull_request.base_branch = base_branch
        pull_request.head_branch = head_branch
        pull_request.status = state
        return pull_request

    pull_request = PullRequest(
        id=uuid.uuid4(),
        repository_id=repository.id,
        pr_number=pr_number,
        title=title,
        author=author,
        base_branch=base_branch,
        head_branch=head_branch,
        status=state,
    )
    db.add(pull_request)
    await db.flush()
    return pull_request


# ---------------------------------------------------------------------------
# GET /reviews/{review_id}
# ---------------------------------------------------------------------------

@router.get("/{review_id}", response_model=ReviewDetailResponse)
async def get_review(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> ReviewDetailResponse:
    """Return a saved review and its related analysis details."""
    result = await db.execute(
        select(Review)
        .options(
            selectinload(Review.findings),
            selectinload(Review.requirement_checks),
            selectinload(Review.changed_files),
        )
        .where(Review.id == review_id)
    )
    review = result.scalar_one_or_none()
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")

    return ReviewDetailResponse(
        review_id=str(review.id),
        created_at=review.created_at,
        task_text=review.task_text,
        risk_score=review.risk_score,
        risk_level=review.risk_level,
        merge_recommendation=review.merge_recommendation,
        report_markdown=review.report_markdown,
        findings=[
            ReviewFindingResponse(
                category=finding.category,
                severity=finding.severity,
                title=finding.title,
                description=finding.description,
                file_path=finding.file_path,
                line_start=finding.line_start,
                line_end=finding.line_end,
                evidence=finding.evidence,
                suggestion=finding.suggestion,
            )
            for finding in review.findings
        ],
        requirement_checks=[
            RequirementCheckResponse(
                requirement_text=check.requirement_text,
                status=check.status,
                evidence=check.evidence,
                reason=check.reason,
            )
            for check in review.requirement_checks
        ],
        changed_files=[
            ChangedFileResponse(
                file_path=changed_file.file_path,
                status=changed_file.status,
                language=changed_file.language,
                additions=changed_file.additions,
                deletions=changed_file.deletions,
                risk_flags=changed_file.risk_flags,
            )
            for changed_file in review.changed_files
        ],
    )


# ---------------------------------------------------------------------------
# POST /reviews/{review_id}/comment
# ---------------------------------------------------------------------------

@router.post("/{review_id}/comment", response_model=ReviewCommentResponse)
async def comment_on_review(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> ReviewCommentResponse:
    """Post a saved PatchProof report as a GitHub PR comment."""
    try:
        result = await post_review_comment(db=db, review_id=review_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PRCommentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ReviewCommentResponse(
        review_id=str(review_id),
        status="posted",
        comment_url=result.comment_url,
    )
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
    return await _analyze_and_save_review(
        db=db,
        task_text=body.task,
        raw_diff=body.diff,
        repo_name=body.repo_name,
        branch=body.branch,
    )


# ---------------------------------------------------------------------------
# POST /reviews/github-pr
# ---------------------------------------------------------------------------

@router.post("/github-pr", response_model=ReviewResponse)
async def create_github_pr_review(
    body: GithubPRReviewRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ReviewResponse:
    """Fetch a GitHub PR by URL, analyze its diff, and save the review."""
    try:
        owner, repo, pr_number = parse_pr_url(body.pr_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    settings = get_settings()
    if not settings.github_token:
        raise HTTPException(
            status_code=400,
            detail="GITHUB_TOKEN is not configured for backend GitHub PR reviews.",
        )

    client = GitHubClient(settings.github_token)
    try:
        metadata = client.fetch_pr_metadata(owner, repo, pr_number)
        raw_diff = client.fetch_pr_diff(owner, repo, pr_number)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    task_text = (body.task or "").strip()
    if not task_text and metadata.body.strip():
        task_text = metadata.body.strip()
    if not task_text and metadata.linked_issue_body:
        task_text = metadata.linked_issue_body.strip()
    if not task_text:
        raise HTTPException(
            status_code=400,
            detail="No task provided. Send task text or add a description to the PR body.",
        )
    if not raw_diff:
        raise HTTPException(status_code=400, detail="No file changes found in this PR.")

    repository = await _get_or_create_repository(
        db,
        owner=metadata.owner,
        name=metadata.repo,
    )
    pull_request = await _get_or_create_pull_request(
        db,
        repository=repository,
        pr_number=metadata.pr_number,
        title=metadata.title,
        author=metadata.author,
        base_branch=metadata.base_branch,
        head_branch=metadata.head_branch,
        state=metadata.state,
    )

    return await _analyze_and_save_review(
        db=db,
        task_text=task_text,
        raw_diff=raw_diff,
        repo_name=f"{metadata.owner}/{metadata.repo}",
        branch=f"PR #{metadata.pr_number}: {metadata.head_branch} -> {metadata.base_branch}",
        repository_id=repository.id,
        pull_request_id=pull_request.id,
    )
