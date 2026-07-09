from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.github_webhook_processor import (
    parse_pull_request_webhook,
    process_pull_request_webhook,
)
from models.github_models import PRMetadata


class AsyncSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _payload(body: str = "Add PDF upload support") -> dict:
    return {
        "action": "opened",
        "installation": {"id": 12345},
        "repository": {"full_name": "ethiyor/patchproof"},
        "pull_request": {"number": 42, "body": body},
    }


def _metadata(body: str = "Fetched PR body", linked_issue_body: str | None = None) -> PRMetadata:
    return PRMetadata(
        owner="ethiyor",
        repo="patchproof",
        pr_number=42,
        title="Add PDF upload support",
        body=body,
        author="ethiyor",
        base_branch="main",
        head_branch="feat/pdf-upload",
        state="open",
        linked_issue_body=linked_issue_body,
    )


class TestParsePullRequestWebhook:
    def test_extracts_required_fields(self):
        event = parse_pull_request_webhook(_payload())

        assert event.action == "opened"
        assert event.installation_id == 12345
        assert event.owner == "ethiyor"
        assert event.repo == "patchproof"
        assert event.repo_full_name == "ethiyor/patchproof"
        assert event.pr_number == 42
        assert event.pr_body == "Add PDF upload support"

    def test_rejects_missing_installation(self):
        payload = _payload()
        payload.pop("installation")

        try:
            parse_pull_request_webhook(payload)
        except ValueError as exc:
            assert "missing installation" in str(exc)
        else:
            raise AssertionError("Expected ValueError")

    def test_rejects_invalid_repo_full_name(self):
        payload = _payload()
        payload["repository"]["full_name"] = "patchproof"

        try:
            parse_pull_request_webhook(payload)
        except ValueError as exc:
            assert "repository.full_name" in str(exc)
        else:
            raise AssertionError("Expected ValueError")

    def test_non_string_pr_body_becomes_empty_string(self):
        payload = _payload()
        payload["pull_request"]["body"] = {"unexpected": "object"}

        event = parse_pull_request_webhook(payload)

        assert event.pr_body == ""


class TestProcessPullRequestWebhook:
    def test_fetches_diff_saves_review_and_posts_comment(self):
        event = parse_pull_request_webhook(_payload())
        db = MagicMock(name="db")
        session_factory = MagicMock(return_value=AsyncSessionContext(db))
        app_client = MagicMock()
        app_client.get_installation_token.return_value = "installation-token"
        github_client = MagicMock()
        github_client.fetch_pr_metadata.return_value = _metadata()
        github_client.fetch_pr_diff.return_value = "diff --git a/app.py b/app.py\n"
        repository = SimpleNamespace(id=uuid.uuid4(), installation_id=None)
        pull_request = SimpleNamespace(id=uuid.uuid4())
        review_id = uuid.uuid4()

        with patch("backend.services.github_webhook_processor.GitHubAppClient", return_value=app_client), \
            patch("backend.services.github_webhook_processor.GitHubClient", return_value=github_client), \
            patch("backend.services.github_webhook_processor.get_session_factory", return_value=session_factory), \
            patch("backend.services.github_webhook_processor._get_or_create_repository", new=AsyncMock(return_value=repository)) as repo_mock, \
            patch("backend.services.github_webhook_processor._get_or_create_pull_request", new=AsyncMock(return_value=pull_request)) as pr_mock, \
            patch("backend.services.github_webhook_processor._analyze_and_save_review", new=AsyncMock(return_value=SimpleNamespace(review_id=str(review_id)))) as analyze_mock, \
            patch("backend.services.github_webhook_processor.post_review_comment", new=AsyncMock()) as comment_mock:
            asyncio.run(process_pull_request_webhook(event))

        app_client.get_installation_token.assert_called_once_with(12345)
        app_client.close.assert_called_once()
        github_client.fetch_pr_metadata.assert_called_once_with("ethiyor", "patchproof", 42)
        github_client.fetch_pr_diff.assert_called_once_with("ethiyor", "patchproof", 42)
        repo_mock.assert_awaited_once_with(db, owner="ethiyor", name="patchproof")
        pr_mock.assert_awaited_once()
        analyze_mock.assert_awaited_once()
        kwargs = analyze_mock.await_args.kwargs
        assert kwargs["db"] is db
        assert kwargs["task_text"] == "Add PDF upload support"
        assert kwargs["raw_diff"] == "diff --git a/app.py b/app.py\n"
        assert kwargs["repo_name"] == "ethiyor/patchproof"
        assert kwargs["branch"] == "PR #42: feat/pdf-upload -> main"
        assert kwargs["repository_id"] == repository.id
        assert kwargs["pull_request_id"] == pull_request.id
        assert repository.installation_id == "12345"
        comment_mock.assert_awaited_once_with(db=db, review_id=review_id)

    def test_falls_back_to_linked_issue_body_when_pr_body_empty(self):
        event = parse_pull_request_webhook(_payload(body=""))
        db = MagicMock(name="db")
        session_factory = MagicMock(return_value=AsyncSessionContext(db))
        app_client = MagicMock()
        app_client.get_installation_token.return_value = "installation-token"
        github_client = MagicMock()
        github_client.fetch_pr_metadata.return_value = _metadata(body="", linked_issue_body="Linked issue task")
        github_client.fetch_pr_diff.return_value = "diff --git a/app.py b/app.py\n"
        repository = SimpleNamespace(id=uuid.uuid4(), installation_id=None)
        pull_request = SimpleNamespace(id=uuid.uuid4())

        with patch("backend.services.github_webhook_processor.GitHubAppClient", return_value=app_client), \
            patch("backend.services.github_webhook_processor.GitHubClient", return_value=github_client), \
            patch("backend.services.github_webhook_processor.get_session_factory", return_value=session_factory), \
            patch("backend.services.github_webhook_processor._get_or_create_repository", new=AsyncMock(return_value=repository)), \
            patch("backend.services.github_webhook_processor._get_or_create_pull_request", new=AsyncMock(return_value=pull_request)), \
            patch("backend.services.github_webhook_processor._analyze_and_save_review", new=AsyncMock(return_value=SimpleNamespace(review_id=str(uuid.uuid4())))) as analyze_mock, \
            patch("backend.services.github_webhook_processor.post_review_comment", new=AsyncMock()):
            asyncio.run(process_pull_request_webhook(event))

        assert analyze_mock.await_args.kwargs["task_text"] == "Linked issue task"

    def test_skips_save_when_diff_is_empty(self):
        event = parse_pull_request_webhook(_payload())
        app_client = MagicMock()
        app_client.get_installation_token.return_value = "installation-token"
        github_client = MagicMock()
        github_client.fetch_pr_metadata.return_value = _metadata()
        github_client.fetch_pr_diff.return_value = ""

        with patch("backend.services.github_webhook_processor.GitHubAppClient", return_value=app_client), \
            patch("backend.services.github_webhook_processor.GitHubClient", return_value=github_client), \
            patch("backend.services.github_webhook_processor._analyze_and_save_review", new=AsyncMock()) as analyze_mock, \
            patch("backend.services.github_webhook_processor.post_review_comment", new=AsyncMock()) as comment_mock:
            asyncio.run(process_pull_request_webhook(event))

        analyze_mock.assert_not_awaited()
        comment_mock.assert_not_awaited()