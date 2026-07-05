import os
from pathlib import Path

import pytest

from core.diff_parser import parse_diff
from core.risk_scorer import compute_risk
from core.report_generator import generate_report, write_report
from models.diff_models import ParsedDiff, ParsedFile
from models.risk_models import RiskScore

FIXTURES = Path(__file__).parent.parent / "fixtures"
GOLDEN_DIR = FIXTURES / "golden_reports"

# Fixed inputs used for the golden snapshot so output is deterministic.
_FIXED_TS = "2026-07-05 00:00 UTC"
_FIXED_TASK = "Update JWT token expiry and add IAT claim."
_FIXED_REPO = "test-repo"
_FIXED_BRANCH = "test-branch"


def _auth_inputs() -> tuple[ParsedDiff, RiskScore]:
    raw = (FIXTURES / "sample_diffs/auth_change.diff").read_text()
    diff = parse_diff(raw)
    risk = compute_risk(diff)
    return diff, risk


# ---------------------------------------------------------------------------
# Section presence
# ---------------------------------------------------------------------------

class TestReportSections:
    def setup_method(self):
        diff, risk = _auth_inputs()
        self.report = generate_report(
            diff=diff, risk=risk,
            task_text=_FIXED_TASK,
            repo_name=_FIXED_REPO,
            branch=_FIXED_BRANCH,
            generated_at=_FIXED_TS,
        )

    def test_has_title(self):
        assert "# PatchProof Report" in self.report

    def test_has_repo_name(self):
        assert "**Repository:** test-repo" in self.report

    def test_has_branch(self):
        assert "**Branch:** test-branch" in self.report

    def test_has_task(self):
        assert _FIXED_TASK in self.report

    def test_has_timestamp(self):
        assert _FIXED_TS in self.report

    def test_has_merge_readiness_section(self):
        assert "## Merge Readiness" in self.report

    def test_has_risk_score_value(self):
        assert "| Risk score | 5 |" in self.report

    def test_has_risk_level(self):
        assert "Medium" in self.report

    def test_has_risk_emoji(self):
        assert "🟡" in self.report

    def test_has_risk_details_section(self):
        assert "## Risk Score Details" in self.report

    def test_has_auth_reason(self):
        assert "auth/security" in self.report

    def test_has_no_tests_reason(self):
        assert "No test files changed" in self.report

    def test_has_risky_files_section(self):
        assert "## Risky Files" in self.report

    def test_risky_file_path_in_table(self):
        assert "`backend/auth/jwt_handler.py`" in self.report

    def test_has_changed_files_section(self):
        assert "## Changed Files" in self.report

    def test_changed_file_in_table(self):
        assert "| `backend/auth/jwt_handler.py`" in self.report

    def test_totals_row_present(self):
        assert "**Total**" in self.report

    def test_has_task_completion_placeholder(self):
        assert "## Task Completion Checklist" in self.report
        assert "Phase 2" in self.report

    def test_has_missing_tests_placeholder(self):
        assert "## Missing Tests" in self.report

    def test_has_final_recommendation_placeholder(self):
        assert "## Final Recommendation" in self.report

    def test_ends_with_newline(self):
        assert self.report.endswith("\n")


# ---------------------------------------------------------------------------
# Risk level colours
# ---------------------------------------------------------------------------

class TestRiskEmoji:
    def _report_for_score(self, score: int, level: str) -> str:
        diff = ParsedDiff(
            files=[], total_files=0, total_additions=0,
            total_deletions=0, has_test_changes=False, risky_files=[]
        )
        risk = RiskScore(score=score, level=level, reasons=[])
        return generate_report(diff, risk, "task", "repo", "main", _FIXED_TS)

    def test_low_emoji(self):
        assert "🟢" in self._report_for_score(1, "low")

    def test_medium_emoji(self):
        assert "🟡" in self._report_for_score(4, "medium")

    def test_high_emoji(self):
        assert "🔴" in self._report_for_score(7, "high")

    def test_critical_emoji(self):
        assert "🚨" in self._report_for_score(10, "critical")


# ---------------------------------------------------------------------------
# No risky files
# ---------------------------------------------------------------------------

class TestNoRiskyFiles:
    def test_no_risky_files_message(self):
        raw = (FIXTURES / "sample_diffs/simple_add.diff").read_text()
        diff = parse_diff(raw)
        risk = compute_risk(diff)
        report = generate_report(diff, risk, "task", "repo", "main", _FIXED_TS)
        assert "No risky files detected." in report

    def test_no_risk_factors_message(self):
        diff = ParsedDiff(
            files=[ParsedFile(path="src/main.py", is_test_file=False)],
            total_files=1, total_additions=5, total_deletions=0,
            has_test_changes=True, risky_files=[],
        )
        risk = RiskScore(score=0, level="low", reasons=[])
        report = generate_report(diff, risk, "task", "repo", "main", _FIXED_TS)
        assert "No risk factors detected." in report


# ---------------------------------------------------------------------------
# Write to disk
# ---------------------------------------------------------------------------

class TestWriteReport:
    def test_creates_file(self, tmp_path):
        diff, risk = _auth_inputs()
        out = tmp_path / "patchproof-report.md"
        write_report(diff, risk, _FIXED_TASK, _FIXED_REPO, _FIXED_BRANCH, out, _FIXED_TS)
        assert out.exists()

    def test_file_content_matches_return_value(self, tmp_path):
        diff, risk = _auth_inputs()
        out = tmp_path / "patchproof-report.md"
        returned = write_report(diff, risk, _FIXED_TASK, _FIXED_REPO, _FIXED_BRANCH, out, _FIXED_TS)
        assert out.read_text(encoding="utf-8") == returned

    def test_file_is_utf8(self, tmp_path):
        diff, risk = _auth_inputs()
        out = tmp_path / "report.md"
        write_report(diff, risk, _FIXED_TASK, _FIXED_REPO, _FIXED_BRANCH, out, _FIXED_TS)
        # emoji characters should survive the round-trip
        content = out.read_text(encoding="utf-8")
        assert "🟡" in content


# ---------------------------------------------------------------------------
# Golden snapshot
# ---------------------------------------------------------------------------

class TestGoldenSnapshot:
    def test_matches_golden_file(self):
        """
        Compare generated output byte-for-byte against the committed golden file.
        If the report format changes, delete tests/fixtures/golden_reports/basic_report.md
        and re-run — the test will recreate it, then pass on the next run.
        """
        diff, risk = _auth_inputs()
        result = generate_report(
            diff=diff, risk=risk,
            task_text=_FIXED_TASK,
            repo_name=_FIXED_REPO,
            branch=_FIXED_BRANCH,
            generated_at=_FIXED_TS,
        )

        golden = GOLDEN_DIR / "basic_report.md"

        if not golden.exists():
            golden.parent.mkdir(parents=True, exist_ok=True)
            golden.write_text(result, encoding="utf-8")
            pytest.skip("Golden file did not exist — created it. Re-run to verify.")

        expected = golden.read_text(encoding="utf-8")
        assert result == expected, (
            "Report does not match golden snapshot.\n"
            "To update: delete tests/fixtures/golden_reports/basic_report.md and re-run."
        )
