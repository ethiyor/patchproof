from pathlib import Path

import pytest

from core.diff_parser import parse_diff
from models.diff_models import ParsedDiff, ParsedFile

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample_diffs"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# simple_add.diff
# One new Python file, non-risky, no tests.
# ---------------------------------------------------------------------------

class TestSimpleAdd:
    def setup_method(self):
        self.result = parse_diff(_load("simple_add.diff"))

    def test_returns_parsed_diff(self):
        assert isinstance(self.result, ParsedDiff)

    def test_file_count(self):
        assert self.result.total_files == 1

    def test_file_path(self):
        assert self.result.files[0].path == "backend/utils/helpers.py"

    def test_file_status_is_added(self):
        assert self.result.files[0].status == "added"

    def test_language_detected(self):
        assert self.result.files[0].language == "python"

    def test_additions_counted(self):
        # 13 lines starting with + in the hunk
        assert self.result.files[0].additions == 13

    def test_no_deletions(self):
        assert self.result.files[0].deletions == 0

    def test_no_risk_flags(self):
        assert self.result.files[0].risk_flags == []

    def test_not_a_test_file(self):
        assert self.result.files[0].is_test_file is False

    def test_one_hunk(self):
        assert len(self.result.files[0].hunks) == 1

    def test_no_test_changes(self):
        assert self.result.has_test_changes is False

    def test_no_risky_files(self):
        assert self.result.risky_files == []

    def test_total_additions(self):
        assert self.result.total_additions == 13

    def test_total_deletions(self):
        assert self.result.total_deletions == 0


# ---------------------------------------------------------------------------
# migration_change.diff
# SQL migration (risky) + Python model change (not risky), no tests.
# ---------------------------------------------------------------------------

class TestMigrationChange:
    def setup_method(self):
        self.result = parse_diff(_load("migration_change.diff"))

    def test_file_count(self):
        assert self.result.total_files == 2

    def test_sql_file_is_present(self):
        paths = [f.path for f in self.result.files]
        assert any(p.endswith(".sql") for p in paths)

    def test_sql_file_status_is_added(self):
        sql = next(f for f in self.result.files if f.path.endswith(".sql"))
        assert sql.status == "added"

    def test_sql_language(self):
        sql = next(f for f in self.result.files if f.path.endswith(".sql"))
        assert sql.language == "sql"

    def test_sql_risk_flag(self):
        sql = next(f for f in self.result.files if f.path.endswith(".sql"))
        assert "migration" in sql.risk_flags

    def test_python_file_status_is_modified(self):
        py = next(f for f in self.result.files if f.path.endswith(".py"))
        assert py.status == "modified"

    def test_python_language(self):
        py = next(f for f in self.result.files if f.path.endswith(".py"))
        assert py.language == "python"

    def test_python_addition(self):
        py = next(f for f in self.result.files if f.path.endswith(".py"))
        assert py.additions == 1

    def test_no_test_changes(self):
        assert self.result.has_test_changes is False

    def test_risky_files_includes_migration(self):
        assert any("migration" in p for p in self.result.risky_files)


# ---------------------------------------------------------------------------
# auth_change.diff
# Single modified auth file (risky), no tests.
# ---------------------------------------------------------------------------

class TestAuthChange:
    def setup_method(self):
        self.result = parse_diff(_load("auth_change.diff"))

    def test_file_count(self):
        assert self.result.total_files == 1

    def test_file_path(self):
        assert self.result.files[0].path == "backend/auth/jwt_handler.py"

    def test_file_status_is_modified(self):
        assert self.result.files[0].status == "modified"

    def test_language(self):
        assert self.result.files[0].language == "python"

    def test_auth_risk_flag(self):
        assert "auth" in self.result.files[0].risk_flags

    def test_additions(self):
        assert self.result.files[0].additions == 2

    def test_deletions(self):
        assert self.result.files[0].deletions == 2

    def test_no_test_changes(self):
        assert self.result.has_test_changes is False

    def test_one_risky_file(self):
        assert len(self.result.risky_files) == 1

    def test_risky_file_path(self):
        assert self.result.risky_files[0] == "backend/auth/jwt_handler.py"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_string(self):
        result = parse_diff("")
        assert result.total_files == 0
        assert result.total_additions == 0
        assert result.total_deletions == 0
        assert result.has_test_changes is False
        assert result.risky_files == []

    def test_whitespace_only(self):
        result = parse_diff("   \n  \n")
        assert result.total_files == 0

    def test_test_file_detected(self):
        raw = _load("simple_add.diff").replace(
            "backend/utils/helpers.py", "tests/unit/test_helpers.py"
        )
        result = parse_diff(raw)
        assert result.has_test_changes is True
        assert result.files[0].is_test_file is True

    def test_risky_files_are_paths(self):
        result = parse_diff(_load("auth_change.diff"))
        assert all(isinstance(p, str) for p in result.risky_files)
