from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from models.diff_models import ParsedDiff

# ---------------------------------------------------------------------------
# Output type
# ---------------------------------------------------------------------------


@dataclass
class TestCaseResult:
    """Whether a single expected test case was found in the diff."""
    __test__ = False  # prevent pytest from collecting this as a test class
    test_case: str
    status: Literal["present", "missing"]


# ---------------------------------------------------------------------------
# Keyword helpers
# ---------------------------------------------------------------------------

# Words too common to be useful as matching signals.
_STOP_WORDS = frozenset({
    "that", "this", "with", "from", "when", "have", "should",
    "does", "test", "file", "case", "code", "data", "list",
    "only", "also", "must", "each", "both",
})


def _keywords(text: str) -> set[str]:
    """
    Extract significant lowercase words (4+ chars, not stop words) from text.

    These are used as matching signals when scanning test hunk lines.
    """
    words = re.findall(r"[a-z_][a-z_]{3,}", text.lower())
    return {w for w in words if w not in _STOP_WORDS}


def _test_content(diff: ParsedDiff) -> str:
    """
    Collect all addition lines (+) from test file hunks into one searchable string.
    """
    parts: list[str] = []
    for f in diff.files:
        if not f.is_test_file:
            continue
        for hunk in f.hunks:
            for line in hunk.lines:
                if line.startswith("+"):
                    parts.append(line[1:].lower())  # strip leading +, lowercase
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main checker
# ---------------------------------------------------------------------------

# Minimum number of keyword matches to consider a test case "present".
_MIN_KEYWORD_MATCHES = 2


def check_test_adequacy(
    expected_test_cases: list[str],
    diff: ParsedDiff,
) -> list[TestCaseResult]:
    """
    Cross-reference expected test cases against test files in the diff.

    Algorithm (heuristic — no LLM):
      1. If no test files changed at all → all cases are ``missing``.
      2. Otherwise, extract addition lines from test hunks into a searchable blob.
      3. For each expected test case, extract keywords and count matches in the blob.
      4. If >= _MIN_KEYWORD_MATCHES keywords match → ``present``, else ``missing``.

    Args:
        expected_test_cases: List from RequirementsOutput.expected_test_cases.
        diff:                 ParsedDiff from parse_diff().

    Returns:
        One TestCaseResult per expected test case, in the same order.
    """
    if not expected_test_cases:
        return []

    # Fast path: no test files touched at all.
    if not diff.has_test_changes:
        return [
            TestCaseResult(test_case=tc, status="missing")
            for tc in expected_test_cases
        ]

    content = _test_content(diff)
    results: list[TestCaseResult] = []

    for tc in expected_test_cases:
        kws = _keywords(tc)
        if not kws:
            # No keywords extractable — cannot determine, treat as missing.
            results.append(TestCaseResult(test_case=tc, status="missing"))
            continue

        matches = sum(1 for kw in kws if kw in content)
        status: Literal["present", "missing"] = (
            "present" if matches >= _MIN_KEYWORD_MATCHES else "missing"
        )
        results.append(TestCaseResult(test_case=tc, status=status))

    return results
