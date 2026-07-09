from __future__ import annotations

import os
import uuid
from types import SimpleNamespace
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from backend.db.models import ChangedFile, PullRequest, Repository, RequirementCheck, Review, ReviewFinding
from backend.db.session import get_db_session
from backend.main import app
from backend.schemas.review_schemas import ReviewResponse
from models.github_models import PRMetadata

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample_diffs"

# ---------------------------------------------------------------------------
# DB session mock
# ---------------------------------------------------------------------------

def _make_mock_session():
    session = MagicMock()
    session.add = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


def _override_db(mock_session):
    async def _mock_get_db():
        yield mock_session
    app.dependency_overrides[get_db_session] = _mock_get_db


def _clear_overrides():
    app.dependency_overrides.clear()


def _no_llm_settings():
    """Return a Settings instance with no API keys, so basic report is used."""
    from backend.config import Settings
    return Settings(openai_api_key="", database_url="", github_token="")


def _github_settings():
    """Return settings with a fake GitHub token and no OpenAI key."""
    from backend.config import Settings
    return Settings(openai_api_key="", database_url="", github_token="ghp_fake1234")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_diff() -> str:
    return (FIXTURES / "simple_add.diff").read_text()


def _auth_diff() -> str:
    return (FIXTURES / "auth_change.diff").read_text()


def _pr_metadata(body: str = "Add PDF upload support") -> PRMetadata:
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
        linked_issue_body="Users should be able to upload PDF files.",
    )


# ---------------------------------------------------------------------------
# GET /reviews/{review_id}
# ---------------------------------------------------------------------------

class TestGetReview:
    def setup_method(self):
        self.mock_db = _make_mock_session()
        _override_db(self.mock_db)
        self.client = TestClient(app)

    def teardown_method(self):
        _clear_overrides()

    def test_returns_saved_review_detail(self):
        review_id = uuid.uuid4()
        review = Review(
            id=review_id,
            task_text="Add PDF upload validation",
            risk_score=7,
            risk_level="high",
            merge_recommendation="needs_changes",
            report_markdown="# PatchProof Report\n...",
        )
        review.created_at = datetime(2026, 7, 6, 12, 30, tzinfo=UTC)
        review.findings = [
            ReviewFinding(
                review_id=review_id,
                category="security",
                severity="error",
                title="No file size limit enforced",
                description="The upload handler accepts arbitrary file size.",
                file_path="backend/routes/upload.py",
                line_start=42,
                line_end=44,
                evidence="No MAX_UPLOAD_SIZE check found",
                suggestion="Reject uploads above the configured limit.",
            )
        ]
        review.requirement_checks = [
            RequirementCheck(
                review_id=review_id,
                requirement_text="Validate MIME type",
                status="missing",
                evidence=None,
                reason="No MIME check found in upload handler",
            )
        ]
        review.changed_files = [
            ChangedFile(
                review_id=review_id,
                file_path="backend/routes/upload.py",
                status="modified",
                language="python",
                additions=15,
                deletions=2,
                risk_flags=["api", "security"],
            )
        ]
        result = MagicMock()
        result.scalar_one_or_none.return_value = review
        self.mock_db.execute = AsyncMock(return_value=result)

        response = self.client.get(f"/reviews/{review_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["review_id"] == str(review_id)
        assert data["task_text"] == "Add PDF upload validation"
        assert data["risk_score"] == 7
        assert data["risk_level"] == "high"
        assert data["merge_recommendation"] == "needs_changes"
        assert data["report_markdown"] == "# PatchProof Report\n..."
        assert data["findings"][0]["title"] == "No file size limit enforced"
        assert data["requirement_checks"][0]["requirement_text"] == "Validate MIME type"
        assert data["changed_files"][0]["file_path"] == "backend/routes/upload.py"

    def test_unknown_review_returns_404(self):
        response = self.client.get(f"/reviews/{uuid.uuid4()}")

        assert response.status_code == 404
        assert response.json() == {"detail": "Review not found"}


# ---------------------------------------------------------------------------
# POST /reviews/local
# ---------------------------------------------------------------------------

class TestCreateLocalReview:
    def setup_method(self):
        self.mock_db = _make_mock_session()
        _override_db(self.mock_db)
        # Patch get_settings so the LLM pipeline is NOT triggered in tests
        self._settings_patch = patch(
            "backend.api.reviews.get_settings",
            return_value=_no_llm_settings(),
        )
        self._settings_patch.start()
        self.client = TestClient(app)

    def teardown_method(self):
        self._settings_patch.stop()
        _clear_overrides()
        from backend.config import get_settings
        get_settings.cache_clear()

    def test_returns_200(self):
        response = self.client.post("/reviews/local", json={
            "task": "Add a utility helper module",
            "diff": _simple_diff(),
        })
        assert response.status_code == 200

    def test_response_has_review_id(self):
        response = self.client.post("/reviews/local", json={
            "task": "Add a utility helper module",
            "diff": _simple_diff(),
        })
        data = response.json()
        assert "review_id" in data
        assert len(data["review_id"]) > 0

    def test_response_has_report_markdown(self):
        response = self.client.post("/reviews/local", json={
            "task": "Add a utility helper module",
            "diff": _simple_diff(),
        })
        data = response.json()
        assert "report_markdown" in data
        assert "# PatchProof Report" in data["report_markdown"]

    def test_response_has_risk_score(self):
        response = self.client.post("/reviews/local", json={
            "task": "Add a utility helper module",
            "diff": _simple_diff(),
        })
        data = response.json()
        assert "risk_score" in data
        assert isinstance(data["risk_score"], int)

    def test_response_has_risk_level(self):
        response = self.client.post("/reviews/local", json={
            "task": "Add auth changes",
            "diff": _auth_diff(),
        })
        data = response.json()
        assert data["risk_level"] in ("low", "medium", "high", "critical")

    def test_response_has_merge_recommendation(self):
        response = self.client.post("/reviews/local", json={
            "task": "Add a utility helper",
            "diff": _simple_diff(),
        })
        data = response.json()
        assert data["merge_recommendation"] in (
            "ready", "ready_with_comments", "needs_changes", "do_not_merge"
        )

    def test_status_is_completed(self):
        response = self.client.post("/reviews/local", json={
            "task": "task",
            "diff": _simple_diff(),
        })
        assert response.json()["status"] == "completed"

    def test_db_add_called(self):
        self.client.post("/reviews/local", json={
            "task": "Add utility module",
            "diff": _simple_diff(),
        })
        assert self.mock_db.add.called

    def test_db_commit_called(self):
        self.client.post("/reviews/local", json={
            "task": "Add utility module",
            "diff": _simple_diff(),
        })
        self.mock_db.commit.assert_awaited_once()

    def test_optional_fields_have_defaults(self):
        response = self.client.post("/reviews/local", json={
            "task": "Add utility module",
            "diff": _simple_diff(),
            # repo_name and branch omitted — should use defaults
        })
        assert response.status_code == 200

    def test_repo_name_appears_in_report(self):
        response = self.client.post("/reviews/local", json={
            "task": "Add utility module",
            "diff": _simple_diff(),
            "repo_name": "myproject",
            "branch": "feat/helper",
        })
        assert "myproject" in response.json()["report_markdown"]

    def test_missing_task_returns_422(self):
        response = self.client.post("/reviews/local", json={
            "diff": _simple_diff(),
            # task missing
        })
        assert response.status_code == 422

    def test_missing_diff_returns_422(self):
        response = self.client.post("/reviews/local", json={
            "task": "some task",
            # diff missing
        })
        assert response.status_code == 422

    def test_auth_diff_has_higher_risk_than_simple(self):
        auth_resp = self.client.post("/reviews/local", json={
            "task": "Update auth", "diff": _auth_diff(),
        }).json()
        simple_resp = self.client.post("/reviews/local", json={
            "task": "Add helper", "diff": _simple_diff(),
        }).json()
        assert auth_resp["risk_score"] > simple_resp["risk_score"]


# ---------------------------------------------------------------------------
# POST /reviews/github-pr
# ---------------------------------------------------------------------------

class TestCreateGithubPRReview:
    def setup_method(self):
        self.mock_db = _make_mock_session()
        _override_db(self.mock_db)
        self._settings_patch = patch(
            "backend.api.reviews.get_settings",
            return_value=_github_settings(),
        )
        self._client_instance = MagicMock()
        self._client_instance.fetch_pr_metadata.return_value = _pr_metadata()
        self._client_instance.fetch_pr_diff.return_value = _auth_diff()
        self._github_client_patch = patch(
            "backend.api.reviews.GitHubClient",
            return_value=self._client_instance,
        )
        self._settings_patch.start()
        self._github_client_patch.start()
        self.client = TestClient(app)

    def teardown_method(self):
        self._github_client_patch.stop()
        self._settings_patch.stop()
        _clear_overrides()
        from backend.config import get_settings
        get_settings.cache_clear()

    def test_returns_200(self):
        response = self.client.post("/reviews/github-pr", json={
            "pr_url": "https://github.com/ethiyor/patchproof/pull/42",
            "task": "Add PDF uploads",
        })
        assert response.status_code == 200

    def test_fetches_metadata_and_diff_for_parsed_url(self):
        self.client.post("/reviews/github-pr", json={
            "pr_url": "https://github.com/ethiyor/patchproof/pull/42",
            "task": "Add PDF uploads",
        })
        self._client_instance.fetch_pr_metadata.assert_called_once_with("ethiyor", "patchproof", 42)
        self._client_instance.fetch_pr_diff.assert_called_once_with("ethiyor", "patchproof", 42)

    def test_response_contains_report(self):
        response = self.client.post("/reviews/github-pr", json={
            "pr_url": "https://github.com/ethiyor/patchproof/pull/42",
            "task": "Add PDF uploads",
        })
        assert "# PatchProof Report" in response.json()["report_markdown"]

    def test_report_uses_repo_and_pr_branch_context(self):
        response = self.client.post("/reviews/github-pr", json={
            "pr_url": "https://github.com/ethiyor/patchproof/pull/42",
            "task": "Add PDF uploads",
        })
        report = response.json()["report_markdown"]
        assert "ethiyor/patchproof" in report
        assert "PR #42: feat/pdf-upload -> main" in report

    def test_uses_request_task_when_provided(self):
        response = self.client.post("/reviews/github-pr", json={
            "pr_url": "https://github.com/ethiyor/patchproof/pull/42",
            "task": "Use this explicit task",
        })
        assert "Use this explicit task" in response.json()["report_markdown"]

    def test_falls_back_to_pr_body_when_task_missing(self):
        response = self.client.post("/reviews/github-pr", json={
            "pr_url": "https://github.com/ethiyor/patchproof/pull/42",
        })
        assert "Add PDF upload support" in response.json()["report_markdown"]

    def test_falls_back_to_linked_issue_body_when_pr_body_empty(self):
        self._client_instance.fetch_pr_metadata.return_value = _pr_metadata(body="")
        response = self.client.post("/reviews/github-pr", json={
            "pr_url": "https://github.com/ethiyor/patchproof/pull/42",
        })
        assert "Users should be able to upload PDF files." in response.json()["report_markdown"]

    def test_persists_repository_pull_request_and_review(self):
        self.client.post("/reviews/github-pr", json={
            "pr_url": "https://github.com/ethiyor/patchproof/pull/42",
            "task": "Add PDF uploads",
        })
        added = [call.args[0] for call in self.mock_db.add.call_args_list]
        assert any(isinstance(obj, Repository) for obj in added)
        assert any(isinstance(obj, PullRequest) for obj in added)
        assert any(isinstance(obj, Review) for obj in added)

    def test_reuses_existing_repository_and_pull_request(self):
        existing_repo = Repository(
            id=uuid.uuid4(),
            owner="ethiyor",
            name="patchproof",
            provider="github",
        )
        existing_pr = PullRequest(
            id=uuid.uuid4(),
            repository_id=existing_repo.id,
            pr_number=42,
        )
        repo_result = MagicMock()
        repo_result.scalar_one_or_none.return_value = existing_repo
        pr_result = MagicMock()
        pr_result.scalar_one_or_none.return_value = existing_pr
        self.mock_db.execute.side_effect = [repo_result, pr_result]

        self.client.post("/reviews/github-pr", json={
            "pr_url": "https://github.com/ethiyor/patchproof/pull/42",
            "task": "Add PDF uploads",
        })

        added = [call.args[0] for call in self.mock_db.add.call_args_list]
        assert not any(isinstance(obj, Repository) for obj in added)
        assert not any(isinstance(obj, PullRequest) for obj in added)
        assert any(isinstance(obj, Review) for obj in added)

    def test_db_commit_called(self):
        self.client.post("/reviews/github-pr", json={
            "pr_url": "https://github.com/ethiyor/patchproof/pull/42",
            "task": "Add PDF uploads",
        })
        self.mock_db.commit.assert_awaited_once()

    def test_invalid_url_returns_400(self):
        response = self.client.post("/reviews/github-pr", json={
            "pr_url": "https://gitlab.com/ethiyor/patchproof/merge_requests/42",
            "task": "Add PDF uploads",
        })
        assert response.status_code == 400
        assert "Invalid GitHub PR URL" in response.json()["detail"]

    def test_missing_github_token_returns_400(self):
        with patch("backend.api.reviews.get_settings", return_value=_no_llm_settings()):
            response = self.client.post("/reviews/github-pr", json={
                "pr_url": "https://github.com/ethiyor/patchproof/pull/42",
                "task": "Add PDF uploads",
            })
        assert response.status_code == 400
        assert "GITHUB_TOKEN" in response.json()["detail"]

    def test_github_fetch_error_returns_502(self):
        self._client_instance.fetch_pr_metadata.side_effect = RuntimeError("GitHub resource not found")
        response = self.client.post("/reviews/github-pr", json={
            "pr_url": "https://github.com/ethiyor/patchproof/pull/42",
            "task": "Add PDF uploads",
        })
        assert response.status_code == 502
        assert "GitHub resource not found" in response.json()["detail"]

    def test_empty_diff_returns_400(self):
        self._client_instance.fetch_pr_diff.return_value = ""
        response = self.client.post("/reviews/github-pr", json={
            "pr_url": "https://github.com/ethiyor/patchproof/pull/42",
            "task": "Add PDF uploads",
        })
        assert response.status_code == 400
        assert "No file changes" in response.json()["detail"]

# ---------------------------------------------------------------------------
# POST /reviews/{review_id}/comment
# ---------------------------------------------------------------------------

class TestCommentOnReview:
    def setup_method(self):
        self.mock_db = _make_mock_session()
        _override_db(self.mock_db)
        self.client = TestClient(app)

    def teardown_method(self):
        _clear_overrides()

    def test_returns_comment_url(self):
        review_id = uuid.uuid4()
        with patch(
            "backend.api.reviews.post_review_comment",
            new=AsyncMock(return_value=SimpleNamespace(comment_url="https://github.com/ethiyor/patchproof/pull/42#issuecomment-1")),
        ) as post_mock:
            response = self.client.post(f"/reviews/{review_id}/comment")

        assert response.status_code == 200
        assert response.json() == {
            "review_id": str(review_id),
            "status": "posted",
            "comment_url": "https://github.com/ethiyor/patchproof/pull/42#issuecomment-1",
        }
        post_mock.assert_awaited_once_with(db=self.mock_db, review_id=review_id)

    def test_unknown_review_returns_404(self):
        review_id = uuid.uuid4()
        with patch(
            "backend.api.reviews.post_review_comment",
            new=AsyncMock(side_effect=LookupError("Review not found")),
        ):
            response = self.client.post(f"/reviews/{review_id}/comment")

        assert response.status_code == 404
        assert response.json() == {"detail": "Review not found"}

    def test_comment_error_returns_400(self):
        from backend.services.pr_commenter import PRCommentError

        review_id = uuid.uuid4()
        with patch(
            "backend.api.reviews.post_review_comment",
            new=AsyncMock(side_effect=PRCommentError("Repository is missing GitHub App installation id.")),
        ):
            response = self.client.post(f"/reviews/{review_id}/comment")

        assert response.status_code == 400
        assert "installation id" in response.json()["detail"]
