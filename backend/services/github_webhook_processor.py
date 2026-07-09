from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from backend.api.reviews import (
    _analyze_and_save_review,
    _get_or_create_pull_request,
    _get_or_create_repository,
)
from backend.db.session import get_session_factory
from backend.services.github_app import GitHubAppClient
from backend.services.pr_commenter import PRCommentError, post_review_comment
from cli.github_client import GitHubClient
from models.github_models import PRMetadata

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PullRequestWebhookEvent:
    """Minimal pull request webhook fields needed for background analysis."""

    action: str | None
    installation_id: int
    owner: str
    repo: str
    repo_full_name: str
    pr_number: int
    pr_body: str


def parse_pull_request_webhook(payload: dict[str, Any]) -> PullRequestWebhookEvent:
    """Extract the fields PatchProof needs from a GitHub pull_request webhook."""
    installation = payload.get("installation")
    repository = payload.get("repository")
    pull_request = payload.get("pull_request")

    if not isinstance(installation, dict) or not isinstance(repository, dict) or not isinstance(pull_request, dict):
        raise ValueError("GitHub pull_request payload is missing installation, repository, or pull_request.")

    installation_id = installation.get("id")
    if not isinstance(installation_id, int):
        raise ValueError("GitHub pull_request payload is missing installation.id.")

    repo_full_name = repository.get("full_name")
    if not isinstance(repo_full_name, str) or "/" not in repo_full_name:
        raise ValueError("GitHub pull_request payload is missing repository.full_name.")
    owner, repo = repo_full_name.split("/", 1)

    pr_number = pull_request.get("number")
    if not isinstance(pr_number, int):
        raise ValueError("GitHub pull_request payload is missing pull_request.number.")

    pr_body = pull_request.get("body")

    return PullRequestWebhookEvent(
        action=payload.get("action") if isinstance(payload.get("action"), str) else None,
        installation_id=installation_id,
        owner=owner,
        repo=repo,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        pr_body=pr_body if isinstance(pr_body, str) else "",
    )


async def process_pull_request_webhook(event: PullRequestWebhookEvent) -> None:
    """Fetch a PR diff using a GitHub App token, analyze it, and save the review."""
    logger.info(
        "Processing GitHub PR webhook: repo=%s pr=%s action=%s installation=%s",
        event.repo_full_name,
        event.pr_number,
        event.action or "unknown",
        event.installation_id,
    )

    app_client = GitHubAppClient()
    try:
        installation_token = app_client.get_installation_token(event.installation_id)
    finally:
        app_client.close()

    github_client = GitHubClient(installation_token)
    metadata = github_client.fetch_pr_metadata(event.owner, event.repo, event.pr_number)
    raw_diff = github_client.fetch_pr_diff(event.owner, event.repo, event.pr_number)
    if not raw_diff:
        logger.info("GitHub PR webhook had no file changes: repo=%s pr=%s", event.repo_full_name, event.pr_number)
        return

    task_text = _resolve_task_text(event=event, metadata=metadata)
    if not task_text:
        logger.info("GitHub PR webhook has no task text: repo=%s pr=%s", event.repo_full_name, event.pr_number)
        return

    factory = get_session_factory()
    async with factory() as db:
        repository = await _get_or_create_repository(db, owner=metadata.owner, name=metadata.repo)
        repository.installation_id = str(event.installation_id)
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
        review_response = await _analyze_and_save_review(
            db=db,
            task_text=task_text,
            raw_diff=raw_diff,
            repo_name=f"{metadata.owner}/{metadata.repo}",
            branch=f"PR #{metadata.pr_number}: {metadata.head_branch} -> {metadata.base_branch}",
            repository_id=repository.id,
            pull_request_id=pull_request.id,
        )
        try:
            await post_review_comment(db=db, review_id=uuid.UUID(review_response.review_id))
        except (PRCommentError, RuntimeError, ValueError) as exc:
            logger.error(
                "Saved GitHub PR review but failed to post comment: repo=%s pr=%s review=%s error=%s",
                event.repo_full_name,
                event.pr_number,
                review_response.review_id,
                exc,
            )


def _resolve_task_text(*, event: PullRequestWebhookEvent, metadata: PRMetadata) -> str:
    """Use webhook PR body first, then fetched PR/linked issue body."""
    for candidate in (event.pr_body, metadata.body, metadata.linked_issue_body or ""):
        task_text = candidate.strip()
        if task_text:
            return task_text
    return ""