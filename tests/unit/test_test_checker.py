from __future__ import annotations

from pathlib import Path

import pytest

from core.diff_parser import parse_diff
from core.test_checker import TestCaseResult, check_test_adequacy
from models.diff_models import ParsedDiff, ParsedFile, Hunk

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample_diffs"


# ---------------------------------------------------------------------------
# Synthetic helpers: build a ParsedDiff that contains a test file with
# specific addition lines, so we can control keyword matching precisely.
# ---------------------------------------------------------------------------

def _diff_with_test_file(addition_lines: list[str]) -> ParsedDiff:
    """Build a minimal ParsedDiff containing one test file with given additions."""
    hunk = Hunk(
        header="@@ -0,0 +1,5 @@",
        lines=[f"+{line}" for line in addition_lines],
        additions=len(addition_lines),
        deletions=0,
    )
    test_file = ParsedFile(
        path="tests/unit/test_upload.py",
        status="added",
        is_test_file=True,
        language="python",
        additions=len(addition_lines),
        deletions=0,
        hunks=[hunk],
    )
    return ParsedDiff(
        files=[test_file],
        total_files=1,
        total_additions=len(addition_lines),
        total_deletions=0,
        has_test_changes=True,
        risky_files=[],
    )


def _diff_no_tests() -> ParsedDiff:
    """ParsedDiff with only production files — no test changes."""
    prod_file = ParsedFile(
        path="backend/routes/upload.py",
        status="modified",
        is_test_file=False,
        language="python",
        additions=10,
        deletions=2,
    )
    return ParsedDiff(
        files=[prod_file],
        total_files=1,
        total_additions=10,
        total_deletions=2,
        has_test_changes=False,
        risky_files=[],
    )


# ---------------------------------------------------------------------------
# No test files in diff
# ---------------------------------------------------------------------------

class TestNoTestFiles:
    def test_all_missing_when_no_test_files(self):
        diff = _diff_no_tests()
        tcs = ["valid upload succeeds", "invalid MIME rejected"]
        results = check_test_adequacy(tcs, diff)
        assert all(r.status == "missing" for r in results)

    def test_count_matches_input(self):
        diff = _diff_no_tests()
        tcs = ["case one", "case two", "case three"]
        assert len(check_test_adequacy(tcs, diff)) == 3

    def test_simple_add_fixture_all_missing(self):
        raw = (FIXTURES / "simple_add.diff").read_text()
        diff = parse_diff(raw)
        tcs = ["valid upload succeeds", "invalid MIME rejected with 400"]
        results = check_test_adequacy(tcs, diff)
        assert all(r.status == "missing" for r in results)

    def test_auth_fixture_all_missing(self):
        raw = (FIXTURES / "auth_change.diff").read_text()
        diff = parse_diff(raw)
        tcs = ["token expiry updated", "IAT claim present in token"]
        results = check_test_adequacy(tcs, diff)
        assert all(r.status == "missing" for r in results)


# ---------------------------------------------------------------------------
# Test files present in diff
# ---------------------------------------------------------------------------

class TestWithTestFile:
    def test_matching_keywords_detected_as_present(self):
        diff = _diff_with_test_file([
            "def test_valid_pdf_upload():",
            "    response = client.post('/upload', files={'file': pdf_bytes})",
            "    assert response.status_code == 200",
            "    assert 'paper_id' in response.json()",
        ])
        tcs = ["valid PDF upload returns 200 with paper_id"]
        results = check_test_adequacy(tcs, diff)
        assert results[0].status == "present"

    def test_unrelated_test_case_is_missing(self):
        diff = _diff_with_test_file([
            "def test_valid_pdf_upload():",
            "    assert response.status_code == 200",
        ])
        tcs = ["payment billing invoice rejected"]
        results = check_test_adequacy(tcs, diff)
        assert results[0].status == "missing"

    def test_partial_match_below_threshold_is_missing(self):
        # Only 1 keyword matches — below the 2-keyword threshold.
        diff = _diff_with_test_file([
            "def test_something_unrelated():",
            "    assert upload is not None",  # 'upload' matches, nothing else
        ])
        tcs = ["validate MIME type rejected with error code"]
        results = check_test_adequacy(tcs, diff)
        assert results[0].status == "missing"

    def test_multiple_test_cases_mixed_results(self):
        diff = _diff_with_test_file([
            "def test_valid_upload_succeeds():",
            "    assert response.status_code == 200",
            "    assert paper_id in body",
        ])
        tcs = [
            "valid upload returns paper_id",          # matches: upload, paper_id, valid → present
            "payment billing invoice rejected",       # no matches → missing
        ]
        results = check_test_adequacy(tcs, diff)
        assert results[0].status == "present"
        assert results[1].status == "missing"

    def test_at_least_one_present_in_realistic_test_file(self):
        """Integration: a realistic test file should match at least one case."""
        diff = _diff_with_test_file([
            "def test_upload_valid_file():",
            "    files = {'upload': ('test.pdf', pdf_bytes, 'application/pdf')}",
            "    response = client.post('/papers/upload', files=files)",
            "    assert response.status_code == 200",
            "    data = response.json()",
            "    assert 'paper_id' in data",
            "",
            "def test_upload_invalid_mime():",
            "    files = {'upload': ('test.txt', b'text', 'text/plain')}",
            "    response = client.post('/papers/upload', files=files)",
            "    assert response.status_code == 400",
        ])
        tcs = [
            "valid PDF upload returns 200 with paper_id",
            "non-PDF MIME type is rejected with 400",
            "file exceeding size limit rejected with 413",  # not in diff → missing
        ]
        results = check_test_adequacy(tcs, diff)
        present = [r for r in results if r.status == "present"]
        missing = [r for r in results if r.status == "missing"]
        assert len(present) >= 1
        assert any("413" in r.test_case for r in missing)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_test_cases_returns_empty_list(self):
        assert check_test_adequacy([], _diff_no_tests()) == []

    def test_test_case_result_has_correct_fields(self):
        diff = _diff_no_tests()
        results = check_test_adequacy(["some test case"], diff)
        assert results[0].test_case == "some test case"
        assert results[0].status in ("present", "missing")

    def test_order_is_preserved(self):
        diff = _diff_no_tests()
        tcs = ["alpha test", "beta test", "gamma test"]
        results = check_test_adequacy(tcs, diff)
        assert [r.test_case for r in results] == tcs
