from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend.db.models import (
    Base,
    ChangedFile,
    PullRequest,
    Repository,
    RequirementCheck,
    Review,
    ReviewFinding,
    User,
)


# ---------------------------------------------------------------------------
# Table names
# ---------------------------------------------------------------------------

class TestTableNames:
    def test_user_table(self):
        assert User.__tablename__ == "users"

    def test_repository_table(self):
        assert Repository.__tablename__ == "repositories"

    def test_pull_request_table(self):
        assert PullRequest.__tablename__ == "pull_requests"

    def test_review_table(self):
        assert Review.__tablename__ == "reviews"

    def test_review_finding_table(self):
        assert ReviewFinding.__tablename__ == "review_findings"

    def test_requirement_check_table(self):
        assert RequirementCheck.__tablename__ == "requirement_checks"

    def test_changed_file_table(self):
        assert ChangedFile.__tablename__ == "changed_files"


# ---------------------------------------------------------------------------
# Model instantiation (Python-level, no DB needed)
# ---------------------------------------------------------------------------

class TestModelInstantiation:
    def test_user_instantiation(self):
        u = User(id=uuid.uuid4(), email="test@example.com",
                 created_at=datetime.now(timezone.utc))
        assert u.email == "test@example.com"

    def test_repository_instantiation(self):
        r = Repository(owner="ethiyor", name="patchproof", provider="github")
        assert r.owner == "ethiyor"
        assert r.provider == "github"

    def test_pull_request_instantiation(self):
        pr = PullRequest(
            repository_id=uuid.uuid4(), pr_number=42,
            title="Add upload", status="open",
        )
        assert pr.pr_number == 42

    def test_review_instantiation(self):
        rev = Review(
            task_text="Add PDF upload",
            risk_score=7,
            risk_level="high",
            merge_recommendation="needs_changes",
        )
        assert rev.risk_level == "high"

    def test_review_finding_instantiation(self):
        f = ReviewFinding(
            review_id=uuid.uuid4(),
            category="security",
            severity="error",
            title="No file size limit",
        )
        assert f.category == "security"

    def test_requirement_check_instantiation(self):
        rc = RequirementCheck(
            review_id=uuid.uuid4(),
            requirement_text="Add MIME validation",
            status="missing",
        )
        assert rc.status == "missing"

    def test_changed_file_instantiation(self):
        cf = ChangedFile(
            review_id=uuid.uuid4(),
            file_path="backend/routes/upload.py",
            status="added",
            additions=42,
            deletions=0,
            risk_flags=["auth", "migration"],
        )
        assert cf.risk_flags == ["auth", "migration"]
        assert cf.additions == 42


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------

class TestRepr:
    def test_user_repr(self):
        uid = uuid.uuid4()
        assert "test@example.com" in repr(User(id=uid, email="test@example.com"))

    def test_repository_repr(self):
        r = Repository(owner="ethiyor", name="patchproof", provider="github")
        assert "ethiyor/patchproof" in repr(r)

    def test_review_repr(self):
        rev = Review(risk_level="high", merge_recommendation="needs_changes")
        assert "high" in repr(rev)

    def test_changed_file_repr(self):
        cf = ChangedFile(
            review_id=uuid.uuid4(),
            file_path="auth/login.py",
            status="modified",
            additions=5,
            deletions=2,
        )
        assert "auth/login.py" in repr(cf)


# ---------------------------------------------------------------------------
# Session factory (no real DB needed — just test it can be created)
# ---------------------------------------------------------------------------

class TestSessionFactory:
    def test_session_factory_can_be_created(self, monkeypatch):
        """Session factory creation should succeed with any URL string."""
        from backend.db import session as db_session

        # Reset cached globals so our monkeypatched settings take effect
        db_session._engine = None
        db_session._session_factory = None

        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/testdb")

        # Clear lru_cache so the monkeypatched env is used
        from backend.config import get_settings
        get_settings.cache_clear()

        factory = db_session.get_session_factory()
        assert factory is not None

        # Cleanup
        db_session._engine = None
        db_session._session_factory = None
        get_settings.cache_clear()
