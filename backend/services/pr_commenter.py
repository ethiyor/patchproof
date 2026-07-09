from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.models import Review
from backend.services.github_app import GitHubAppClient
from cli.github_client import GitHubClient

logger = logging.getLogger(__name__)

_COMMENT_MARKER = "<!-- patchproof-review -->"
_FOOTER = "_Posted by PatchProof._"


class PRCommentError(RuntimeError):
    """Raised when a saved review cannot be posted to GitHub."""


@dataclass(frozen=True)
class PRCommentResult:
    """Result returned after a PR comment is created."""

    comment_url: str


def format_report_for_github(report_markdown: str) -> str:
    """Wrap a saved PatchProof report in a stable GitHub comment envelope."""
    report = report_markdown.strip()
    if not report:
        raise PRCommentError("Review has no report Markdown to post.")

    parts = [_COMMENT_MARKER]
    if not report.lstrip().startswith("#"):
        parts.append("# PatchProof Report")
    parts.append(report)
    parts.append("---")
    parts.append(_FOOTER)
    return "\n\n".join(parts) + "\n"


def post_pr_comment(
    *,
    owner: str,
    repo: str,
    pr_number: int,
    report_markdown: str,
    installation_token: str,
    github_client_factory: type[GitHubClient] = GitHubClient,
) -> PRCommentResult:
    """Post a PatchProof report to a GitHub PR conversation."""
    body = format_report_for_github(report_markdown)
    github_client = github_client_factory(installation_token)
    try:
        comment_url = github_client.create_issue_comment(owner, repo, pr_number, body)
    except RuntimeError as exc:
        logger.error(
            "Failed to post PatchProof PR comment: repo=%s/%s pr=%s error=%s",
            owner,
            repo,
            pr_number,
            exc,
        )
        raise PRCommentError(str(exc)) from exc
    return PRCommentResult(comment_url=comment_url)


async def post_review_comment(
    *,
    db: AsyncSession,
    review_id: uuid.UUID,
    app_client_factory: type[GitHubAppClient] = GitHubAppClient,
    github_client_factory: type[GitHubClient] = GitHubClient,
) -> PRCommentResult:
    """Load a saved review and post its Markdown report to the linked GitHub PR."""
    result = await db.execute(
        select(Review)
        .options(
            selectinload(Review.repository),
            selectinload(Review.pull_request),
        )
        .where(Review.id == review_id)
    )
    review = result.scalar_one_or_none()
    if review is None:
        raise LookupError("Review not found")
    if review.repository is None or review.pull_request is None:
        raise PRCommentError("Review is not linked to a GitHub pull request.")
    if not review.repository.installation_id:
        raise PRCommentError("Repository is missing GitHub App installation id.")
    if not review.report_markdown:
        raise PRCommentError("Review has no report Markdown to post.")

    app_client = app_client_factory()
    try:
        installation_token = app_client.get_installation_token(int(review.repository.installation_id))
    finally:
        app_client.close()

    return post_pr_comment(
        owner=review.repository.owner,
        repo=review.repository.name,
        pr_number=review.pull_request.pr_number,
        report_markdown=review.report_markdown,
        installation_token=installation_token,
        github_client_factory=github_client_factory,
    )