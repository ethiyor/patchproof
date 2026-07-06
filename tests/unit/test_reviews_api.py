from __future__ import annotations

import os
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from backend.db.session import get_db_session
from backend.main import app
from backend.schemas.review_schemas import ReviewResponse

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample_diffs"

# ---------------------------------------------------------------------------
# DB session mock
# ---------------------------------------------------------------------------

def _make_mock_session():
    session = MagicMock()
    session.add = MagicMock()
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_diff() -> str:
    return (FIXTURES / "simple_add.diff").read_text()


def _auth_diff() -> str:
    return (FIXTURES / "auth_change.diff").read_text()


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
