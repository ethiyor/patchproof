from __future__ import annotations

from models.diff_models import ParsedDiff
from models.risk_models import RiskLevel, RiskScore

# ---------------------------------------------------------------------------
# Scoring thresholds
# ---------------------------------------------------------------------------

_THRESHOLDS: list[tuple[int, RiskLevel]] = [
    (9, "critical"),
    (6, "high"),
    (3, "medium"),
    (0, "low"),
]


def _level(score: int) -> RiskLevel:
    for threshold, level in _THRESHOLDS:
        if score >= threshold:
            return level
    return "low"


# ---------------------------------------------------------------------------
# Rule-based scorer
# ---------------------------------------------------------------------------

def compute_risk(diff: ParsedDiff) -> RiskScore:
    """
    Apply the rule-based scoring table to a ParsedDiff and return a RiskScore.

    Rules (from docs/07_risk_scoring_and_report.md):

        +3  touches auth / security
        +3  touches payments / billing
        +2  database migration file present
        +2  no test files changed  (or -2 if tests were changed)
        +2  file upload / user input area touched
        +2  public API routes changed
        +1  config / env file touched
        +1  PR has more than 500 lines changed
        +1  more than 10 files changed
        +1  middleware touched

    Score is floored at 0.
    Levels:  0-2 low  |  3-5 medium  |  6-8 high  |  9+ critical
    """
    score = 0
    reasons: list[str] = []

    # Collect the union of all risk flags across all files in the diff
    all_flags: set[str] = set()
    for f in diff.files:
        all_flags.update(f.risk_flags)

    # --- Auth / security (+3) ---
    AUTH_FLAGS = {"auth", "login", "permissions", "security"}
    if all_flags & AUTH_FLAGS:
        score += 3
        matched = sorted(all_flags & AUTH_FLAGS)
        reasons.append(f"Touches auth/security ({', '.join(matched)}) (+3)")

    # --- Payments / billing (+3) ---
    PAYMENT_FLAGS = {"payments", "billing"}
    if all_flags & PAYMENT_FLAGS:
        score += 3
        matched = sorted(all_flags & PAYMENT_FLAGS)
        reasons.append(f"Touches payments/billing ({', '.join(matched)}) (+3)")

    # --- Database migration (+2) ---
    if "migration" in all_flags:
        score += 2
        reasons.append("Database migration file modified (+2)")

    # --- Test changes (+2 / -2) ---
    # Only apply the no-test penalty when there are actual production files changed.
    if diff.total_files > 0:
        if not diff.has_test_changes:
            score += 2
            reasons.append("No test files changed (+2)")
        else:
            score -= 2
            reasons.append("Tests added or updated (-2)")

    # --- API routes changed (+2) ---
    if "routes" in all_flags:
        score += 2
        reasons.append("Public API routes changed (+2)")

    # --- Config / env file (+1) ---
    CONFIG_FLAGS = {"config", "env_file"}
    if all_flags & CONFIG_FLAGS:
        score += 1
        reasons.append("Config/env file touched (+1)")

    # --- Large diff (+1) ---
    total_lines = diff.total_additions + diff.total_deletions
    if total_lines > 500:
        score += 1
        reasons.append(f"Large PR ({total_lines} lines changed) (+1)")

    # --- Many files (+1) ---
    if diff.total_files > 10:
        score += 1
        reasons.append(f"Many files changed ({diff.total_files}) (+1)")

    # --- Middleware (+1) ---
    if "middleware" in all_flags:
        score += 1
        reasons.append("Middleware touched (+1)")

    # Floor at 0
    score = max(0, score)

    return RiskScore(score=score, level=_level(score), reasons=reasons)
