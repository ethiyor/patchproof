from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, call

import pytest
from pydantic import ValidationError

from core.verification_engine import verify_requirements, _verify_one
from models.llm_outputs import VerificationResult
from tests.mocks.llm_responses import (
    STEP3_MISSING,
    STEP3_SATISFIED,
    STEP3_PARTIAL,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample_diffs"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patch_llm(return_value: dict):
    return patch("core.verification_engine.call_llm", return_value=return_value)

def _patch_llm_side_effect(side_effect):
    return patch("core.verification_engine.call_llm", side_effect=side_effect)


# ---------------------------------------------------------------------------
# _verify_one — single requirement
# ---------------------------------------------------------------------------

class TestVerifyOne:
    def test_returns_verification_result(self):
        with _patch_llm(STEP3_SATISFIED):
            result = _verify_one("Create upload endpoint", "diff text")
        assert isinstance(result, VerificationResult)

    def test_satisfied_result_preserved(self):
        with _patch_llm(STEP3_SATISFIED):
            result = _verify_one("Create upload endpoint", "diff text")
        assert result.status == "satisfied"
        assert len(result.evidence) > 0

    def test_missing_result_preserved(self):
        with _patch_llm(STEP3_MISSING):
            result = _verify_one("Validate MIME type", "diff text")
        assert result.status == "missing"
        assert result.reason

    def test_partial_result_preserved(self):
        with _patch_llm(STEP3_PARTIAL):
            result = _verify_one("Return structured errors", "diff text")
        assert result.status == "partially_satisfied"

    def test_requirement_in_user_message(self):
        req = "Create a POST /papers/upload endpoint"
        with patch("core.verification_engine.call_llm", return_value=STEP3_SATISFIED) as mock_llm:
            _verify_one(req, "diff")
        user_content = mock_llm.call_args[0][0][1]["content"]
        assert req in user_content

    def test_system_prompt_is_step3(self):
        with patch("core.verification_engine.call_llm", return_value=STEP3_SATISFIED) as mock_llm:
            _verify_one("req", "diff")
        system_content = mock_llm.call_args[0][0][0]["content"]
        assert "satisfied" in system_content.lower()

    def test_large_diff_is_truncated(self):
        large_diff = "+" + "x" * 40_000
        with patch("core.verification_engine.call_llm", return_value=STEP3_SATISFIED) as mock_llm:
            _verify_one("req", large_diff)
        user_content = mock_llm.call_args[0][0][1]["content"]
        assert "truncated" in user_content

    def test_repo_context_included_when_provided(self):
        ctx = "class Paper: pass"
        with patch("core.verification_engine.call_llm", return_value=STEP3_SATISFIED) as mock_llm:
            _verify_one("req", "diff", repo_context=ctx)
        user_content = mock_llm.call_args[0][0][1]["content"]
        assert ctx in user_content

    def test_no_repo_context_by_default(self):
        with patch("core.verification_engine.call_llm", return_value=STEP3_SATISFIED) as mock_llm:
            _verify_one("req", "diff")
        user_content = mock_llm.call_args[0][0][1]["content"]
        # Without context the "Repository context:" section is not included
        assert "Repository context:" not in user_content


# ---------------------------------------------------------------------------
# Evidence enforcement + downgrade
# ---------------------------------------------------------------------------

class TestEvidenceEnforcement:
    def test_satisfied_without_evidence_triggers_retry(self):
        """Pydantic rejects satisfied+no evidence → retry fires."""
        satisfied_no_evidence = {**STEP3_SATISFIED, "evidence": []}
        call_count = 0

        def side_effect(messages, **kwargs):
            nonlocal call_count
            call_count += 1
            return satisfied_no_evidence if call_count == 1 else STEP3_SATISFIED

        with _patch_llm_side_effect(side_effect):
            result = _verify_one("req", "diff")

        assert call_count == 2
        assert result.status == "satisfied"

    def test_consistently_bad_evidence_downgrades_to_unclear(self):
        """After all retries fail, status is forced to 'unclear' — no crash."""
        bad = {**STEP3_SATISFIED, "evidence": []}  # always fails validation

        with _patch_llm(bad):
            result = _verify_one("req", "diff")

        assert result.status == "unclear"
        assert result.evidence == []
        assert "Could not verify" in result.reason

    def test_downgraded_result_contains_original_requirement(self):
        bad = {**STEP3_SATISFIED, "evidence": []}
        req = "Validate MIME type"

        with _patch_llm(bad):
            result = _verify_one(req, "diff")

        assert result.requirement == req


# ---------------------------------------------------------------------------
# verify_requirements — full list
# ---------------------------------------------------------------------------

class TestVerifyRequirements:
    def test_returns_list_of_results(self):
        reqs = ["req 1", "req 2", "req 3"]
        with _patch_llm(STEP3_SATISFIED):
            results = verify_requirements(reqs, "diff")
        assert len(results) == 3
        assert all(isinstance(r, VerificationResult) for r in results)

    def test_empty_requirements_returns_empty_list(self):
        results = verify_requirements([], "diff")
        assert results == []

    def test_order_is_preserved(self):
        reqs = ["req A", "req B", "req C"]
        responses = [STEP3_SATISFIED, STEP3_MISSING, STEP3_PARTIAL]
        call_count = 0

        def side_effect(messages, **kwargs):
            nonlocal call_count
            resp = responses[call_count]
            call_count += 1
            return resp

        with _patch_llm_side_effect(side_effect):
            results = verify_requirements(reqs, "diff")

        assert results[0].status == "satisfied"
        assert results[1].status == "missing"
        assert results[2].status == "partially_satisfied"

    def test_parallel_execution_returns_same_count(self):
        reqs = ["req 1", "req 2", "req 3", "req 4"]
        with _patch_llm(STEP3_SATISFIED):
            results = verify_requirements(reqs, "diff", max_workers=2)
        assert len(results) == 4

    def test_uses_fixture_diffs(self):
        """Integration: verify against real sample diffs with mocked LLM."""
        raw = (FIXTURES / "auth_change.diff").read_text()
        reqs = ["Update JWT token expiry", "Add IAT claim to token"]

        with _patch_llm(STEP3_SATISFIED):
            results = verify_requirements(reqs, raw)

        assert len(results) == 2
