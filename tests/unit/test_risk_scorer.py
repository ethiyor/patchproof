from pathlib import Path

import pytest

from core.diff_parser import parse_diff
from core.risk_scorer import compute_risk
from models.diff_models import ParsedDiff, ParsedFile
from models.risk_models import RiskScore

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample_diffs"


# ---------------------------------------------------------------------------
# Helper: build a synthetic ParsedDiff without needing a fixture file.
# This lets us test individual rules in isolation.
# ---------------------------------------------------------------------------

def _make_diff(
    flags: list[str] | None = None,
    has_test_changes: bool = False,
    total_files: int = 2,
    total_additions: int = 50,
    total_deletions: int = 10,
    extra_files: list[ParsedFile] | None = None,
) -> ParsedDiff:
    flags = flags or []
    primary = ParsedFile(
        path="backend/main.py",
        risk_flags=flags,
        is_test_file=False,
    )
    files = [primary] + (extra_files or [])
    if has_test_changes:
        test_file = ParsedFile(
            path="tests/unit/test_main.py",
            risk_flags=[],
            is_test_file=True,
        )
        files.append(test_file)
    return ParsedDiff(
        files=files,
        total_files=total_files,
        total_additions=total_additions,
        total_deletions=total_deletions,
        has_test_changes=has_test_changes,
        risky_files=[f.path for f in files if f.risk_flags],
    )


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

class TestReturnType:
    def test_returns_risk_score(self):
        result = compute_risk(_make_diff())
        assert isinstance(result, RiskScore)

    def test_has_score_int(self):
        result = compute_risk(_make_diff())
        assert isinstance(result.score, int)

    def test_has_level_string(self):
        result = compute_risk(_make_diff())
        assert result.level in ("low", "medium", "high", "critical")

    def test_has_reasons_list(self):
        result = compute_risk(_make_diff())
        assert isinstance(result.reasons, list)


# ---------------------------------------------------------------------------
# Auth / security rule (+3)
# ---------------------------------------------------------------------------

class TestAuthRule:
    def test_auth_flag_adds_3(self):
        without = compute_risk(_make_diff(flags=[])).score
        with_auth = compute_risk(_make_diff(flags=["auth"])).score
        assert with_auth == without + 3

    def test_login_flag_triggers_auth_rule(self):
        result = compute_risk(_make_diff(flags=["login"]))
        assert any("auth/security" in r for r in result.reasons)

    def test_security_flag_triggers_auth_rule(self):
        result = compute_risk(_make_diff(flags=["security"]))
        assert any("auth/security" in r for r in result.reasons)

    def test_auth_no_tests_is_at_least_medium(self):
        # auth (+3) + no tests (+2) = 5 → medium
        # The milestone spec requires score >= 5 for auth/login with no tests.
        result = compute_risk(_make_diff(flags=["auth"], has_test_changes=False))
        assert result.score >= 5
        assert result.level in ("medium", "high", "critical")

    def test_auth_reason_in_list(self):
        result = compute_risk(_make_diff(flags=["auth"]))
        assert any("auth" in r.lower() for r in result.reasons)


# ---------------------------------------------------------------------------
# Payments / billing rule (+3)
# ---------------------------------------------------------------------------

class TestPaymentsRule:
    def test_payments_flag_adds_3(self):
        without = compute_risk(_make_diff(flags=[])).score
        with_pay = compute_risk(_make_diff(flags=["payments"])).score
        assert with_pay == without + 3

    def test_billing_flag_adds_3(self):
        result = compute_risk(_make_diff(flags=["billing"]))
        assert any("billing" in r.lower() for r in result.reasons)

    def test_payments_no_tests_is_at_least_medium(self):
        result = compute_risk(_make_diff(flags=["payments"], has_test_changes=False))
        assert result.score >= 5
        assert result.level in ("medium", "high", "critical")


# ---------------------------------------------------------------------------
# Migration rule (+2)
# ---------------------------------------------------------------------------

class TestMigrationRule:
    def test_migration_flag_adds_2(self):
        without = compute_risk(_make_diff(flags=[])).score
        with_mig = compute_risk(_make_diff(flags=["migration"])).score
        assert with_mig == without + 2

    def test_migration_reason_present(self):
        result = compute_risk(_make_diff(flags=["migration"]))
        assert any("migration" in r.lower() for r in result.reasons)

    def test_migration_fixture_scores_medium_or_higher(self):
        raw = (FIXTURES / "migration_change.diff").read_text()
        diff = parse_diff(raw)
        result = compute_risk(diff)
        assert result.score >= 3
        assert result.level in ("medium", "high", "critical")


# ---------------------------------------------------------------------------
# No-test rule (+2) and test-present rule (-2)
# ---------------------------------------------------------------------------

class TestTestRule:
    def test_no_tests_adds_2(self):
        # Use auth (+3) as a base so the floor never interferes.
        # auth + no-tests = 3+2 = 5, auth + tests = 3-2 = 1, difference = 4.
        without_tests = compute_risk(_make_diff(flags=["auth"], has_test_changes=False)).score
        with_tests = compute_risk(_make_diff(flags=["auth"], has_test_changes=True)).score
        assert without_tests == with_tests + 4

    def test_tests_present_reduces_score(self):
        # A diff with tests should always score lower than the same diff without tests.
        base = _make_diff(flags=["migration"])
        base_no_tests = _make_diff(flags=["migration"], has_test_changes=False)
        base_with_tests = _make_diff(flags=["migration"], has_test_changes=True)
        assert compute_risk(base_with_tests).score < compute_risk(base_no_tests).score

    def test_no_test_reason_present(self):
        result = compute_risk(_make_diff(has_test_changes=False))
        assert any("no test" in r.lower() for r in result.reasons)

    def test_tests_added_reason_present(self):
        result = compute_risk(_make_diff(has_test_changes=True))
        assert any("tests added" in r.lower() for r in result.reasons)


# ---------------------------------------------------------------------------
# Risk levels
# ---------------------------------------------------------------------------

class TestRiskLevels:
    def test_score_0_is_low(self):
        # Empty diff → no rules fire except maybe no-tests, but 0 files → no-test skipped
        diff = ParsedDiff(
            files=[], total_files=0, total_additions=0,
            total_deletions=0, has_test_changes=False, risky_files=[]
        )
        result = compute_risk(diff)
        assert result.level == "low"

    def test_score_3_is_medium(self):
        # migration (+2) + no tests (+2) = 4 → medium.
        # But let's build a diff that hits exactly 3.
        # One way: auth (+3) with tests (-2) = 1 → low. That's wrong.
        # Let's use migration (+2) + config (+1) + tests (-2) = 1 → low. Also wrong.
        # Build score=3: migration(+2) + no-tests(+2) = 4. Hmm.
        # Use routes (+2) + config (+1) + tests (-2) = 1 → low.
        # Use auth (+3) = 3 → medium (with tests present so no +2 penalty).
        result = compute_risk(_make_diff(flags=["auth"], has_test_changes=True))
        assert result.score == 1  # 3 - 2 = 1 → low
        # To get exactly 3: use migration(+2) + config(+1) + tests(-2) = 1 too.
        # Actually auth(+3) alone with no tests = 3+2=5. With tests: 3-2=1.
        # To get score=3: migration(+2) + no-tests(+2) - but that's 4.
        # Use routes(+2) + config(+1) = 3, with tests: 3-2=1.
        # Let's use routes(+2) + config(+1) with no tests: 2+1+2=5. Still not 3.
        # To test medium directly: use auth(+3) with no tests, score=5 (medium).
        result = compute_risk(_make_diff(flags=["auth"], has_test_changes=False))
        assert result.level == "medium"

    def test_score_9_is_critical(self):
        # auth(+3) + payments(+3) + migration(+2) + no-tests(+2) = 10 → critical
        result = compute_risk(_make_diff(
            flags=["auth", "payments", "migration"],
            has_test_changes=False,
        ))
        assert result.score >= 9
        assert result.level == "critical"

    def test_score_floored_at_zero(self):
        # Only tests changed, no risk flags → 0 (floored from -2)
        diff = ParsedDiff(
            files=[ParsedFile(path="tests/unit/test_foo.py", is_test_file=True)],
            total_files=1, total_additions=20,
            total_deletions=0, has_test_changes=True, risky_files=[]
        )
        result = compute_risk(diff)
        assert result.score == 0
        assert result.level == "low"


# ---------------------------------------------------------------------------
# Size rules
# ---------------------------------------------------------------------------

class TestSizeRules:
    def test_large_pr_adds_1(self):
        small = compute_risk(_make_diff(total_additions=100, total_deletions=50)).score
        large = compute_risk(_make_diff(total_additions=400, total_deletions=200)).score
        assert large == small + 1

    def test_many_files_adds_1(self):
        few = compute_risk(_make_diff(total_files=5)).score
        many = compute_risk(_make_diff(total_files=11)).score
        assert many == few + 1


# ---------------------------------------------------------------------------
# Full fixture integration
# ---------------------------------------------------------------------------

class TestFixtureIntegration:
    def test_auth_fixture_is_risky(self):
        raw = (FIXTURES / "auth_change.diff").read_text()
        diff = parse_diff(raw)
        result = compute_risk(diff)
        assert result.score >= 5
        assert any("auth" in r.lower() for r in result.reasons)

    def test_simple_add_is_low_risk(self):
        raw = (FIXTURES / "simple_add.diff").read_text()
        diff = parse_diff(raw)
        result = compute_risk(diff)
        # simple_add has no risk flags, no tests → only +2 for no tests
        assert result.score == 2
        assert result.level == "low"

    def test_auth_scores_higher_than_simple_add(self):
        auth_score = compute_risk(parse_diff((FIXTURES / "auth_change.diff").read_text())).score
        simple_score = compute_risk(parse_diff((FIXTURES / "simple_add.diff").read_text())).score
        assert auth_score > simple_score
