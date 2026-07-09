from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.db.models import PullRequest, Repository, Review
from backend.services.pr_commenter import (
    PRCommentError,
    format_report_for_github,
    post_pr_comment,
    post_review_comment,
)


def _review() -> Review:
    repo = Repository(
        id=uuid.uuid4(),
        owner="ethiyor",
        name="patchproof",
        provider="github",
        installation_id="12345",
    )
    pr = PullRequest(
        id=uuid.uuid4(),
        repository_id=repo.id,
        pr_number=42,
        title="Add PDF uploads",
    )
    review = Review(
        id=uuid.uuid4(),
        repository_id=repo.id,
        pull_request_id=pr.id,
        report_markdown="# PatchProof Report\n\n| Result | Value |\n| --- | --- |\n| Risk | Low |",
    )
    review.repository = repo
    review.pull_request = pr
    return review


class TestFormatReportForGithub:
    def test_wraps_report_with_marker_and_footer(self):
        body = format_report_for_github("# PatchProof Report\n\n```python\nprint('ok')\n```")

        assert body.startswith("<!-- patchproof-review -->")
        assert "# PatchProof Report" in body
        assert "```python" in body
        assert "_Posted by PatchProof._" in body

    def test_adds_heading_when_report_has_no_heading(self):
        body = format_report_for_github("Plain report body")

        assert "# PatchProof Report" in body
        assert "Plain report body" in body

    def test_rejects_empty_report(self):
        with pytest.raises(PRCommentError, match="no report"):
            format_report_for_github("   ")


class TestPostPrComment:
    def test_posts_comment_and_returns_url(self):
        github_client = MagicMock()
        github_client.create_issue_comment.return_value = "https://github.com/ethiyor/patchproof/pull/42#issuecomment-1"
        factory = MagicMock(return_value=github_client)

        result = post_pr_comment(
            owner="ethiyor",
            repo="patchproof",
            pr_number=42,
            report_markdown="# PatchProof Report",
            installation_token="token",
            github_client_factory=factory,
        )

        factory.assert_called_once_with("token")
        github_client.create_issue_comment.assert_called_once()
        args = github_client.create_issue_comment.call_args.args
        assert args[:3] == ("ethiyor", "patchproof", 42)
        assert "# PatchProof Report" in args[3]
        assert result.comment_url.endswith("issuecomment-1")

    def test_wraps_github_failure(self):
        github_client = MagicMock()
        github_client.create_issue_comment.side_effect = RuntimeError("GitHub denied comment")
        factory = MagicMock(return_value=github_client)

        with pytest.raises(PRCommentError, match="GitHub denied comment"):
            post_pr_comment(
                owner="ethiyor",
                repo="patchproof",
                pr_number=42,
                report_markdown="# PatchProof Report",
                installation_token="token",
                github_client_factory=factory,
            )

        github_client.create_issue_comment.assert_called_once()


class TestPostReviewComment:
    def test_loads_review_gets_token_and_posts_comment(self):
        review = _review()
        result = MagicMock()
        result.scalar_one_or_none.return_value = review
        db = MagicMock()
        db.execute = AsyncMock(return_value=result)
        app_client = MagicMock()
        app_client.get_installation_token.return_value = "installation-token"
        app_factory = MagicMock(return_value=app_client)
        github_client = MagicMock()
        github_client.create_issue_comment.return_value = "https://github.com/ethiyor/patchproof/pull/42#issuecomment-1"
        github_factory = MagicMock(return_value=github_client)

        response = asyncio.run(post_review_comment(
            db=db,
            review_id=review.id,
            app_client_factory=app_factory,
            github_client_factory=github_factory,
        ))

        app_client.get_installation_token.assert_called_once_with(12345)
        app_client.close.assert_called_once()
        github_factory.assert_called_once_with("installation-token")
        github_client.create_issue_comment.assert_called_once()
        assert response.comment_url.endswith("issuecomment-1")

    def test_unknown_review_raises_lookup_error(self):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db = MagicMock()
        db.execute = AsyncMock(return_value=result)

        with pytest.raises(LookupError, match="Review not found"):
            asyncio.run(post_review_comment(db=db, review_id=uuid.uuid4()))

    def test_missing_installation_id_raises_clear_error(self):
        review = _review()
        review.repository.installation_id = None
        result = MagicMock()
        result.scalar_one_or_none.return_value = review
        db = MagicMock()
        db.execute = AsyncMock(return_value=result)

        with pytest.raises(PRCommentError, match="installation id"):
            asyncio.run(post_review_comment(db=db, review_id=review.id))