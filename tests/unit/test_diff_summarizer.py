from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from core.diff_summarizer import summarize_diff
from models.llm_outputs import DiffSummaryOutput
from tests.mocks.llm_responses import STEP2_DIFF_SUMMARY

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample_diffs"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _patch_llm(return_value: dict):
    return patch("core.diff_summarizer.call_llm", return_value=return_value)

def _patch_llm_side_effect(side_effect):
    return patch("core.diff_summarizer.call_llm", side_effect=side_effect)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestSummarizeDiffSuccess:
    def test_returns_diff_summary_output(self):
        with _patch_llm(STEP2_DIFF_SUMMARY):
            result = summarize_diff("diff --git a/x b/x\n+added")
        assert isinstance(result, DiffSummaryOutput)

    def test_change_summary_populated(self):
        with _patch_llm(STEP2_DIFF_SUMMARY):
            result = summarize_diff("diff")
        assert result.change_summary == STEP2_DIFF_SUMMARY["change_summary"]

    def test_implemented_areas_populated(self):
        with _patch_llm(STEP2_DIFF_SUMMARY):
            result = summarize_diff("diff")
        assert len(result.implemented_areas) > 0

    def test_unrelated_changes_is_list(self):
        with _patch_llm(STEP2_DIFF_SUMMARY):
            result = summarize_diff("diff")
        assert isinstance(result.unrelated_changes, list)

    def test_system_prompt_is_step2(self):
        with patch("core.diff_summarizer.call_llm", return_value=STEP2_DIFF_SUMMARY) as mock_llm:
            summarize_diff("some diff text")
        messages = mock_llm.call_args[0][0]
        assert messages[0]["role"] == "system"
        assert "diff" in messages[0]["content"].lower()

    def test_diff_text_is_in_user_message(self):
        diff = "diff --git a/main.py b/main.py\n+print('hello')"
        with patch("core.diff_summarizer.call_llm", return_value=STEP2_DIFF_SUMMARY) as mock_llm:
            summarize_diff(diff)
        messages = mock_llm.call_args[0][0]
        assert diff in messages[1]["content"]

    def test_works_with_real_fixture(self):
        raw = (FIXTURES / "simple_add.diff").read_text()
        with _patch_llm(STEP2_DIFF_SUMMARY):
            result = summarize_diff(raw)
        assert isinstance(result, DiffSummaryOutput)
        assert result.change_summary


# ---------------------------------------------------------------------------
# Large diff truncation
# ---------------------------------------------------------------------------

class TestLargeDiffTruncation:
    def test_large_diff_is_truncated_in_user_message(self):
        large_diff = "+" + "x" * 70_000
        with patch("core.diff_summarizer.call_llm", return_value=STEP2_DIFF_SUMMARY) as mock_llm:
            summarize_diff(large_diff)
        user_content = mock_llm.call_args[0][0][1]["content"]
        assert "truncated" in user_content
        assert len(user_content) < len(large_diff)

    def test_small_diff_is_not_truncated(self):
        small_diff = "diff --git a/x b/x\n+one line"
        with patch("core.diff_summarizer.call_llm", return_value=STEP2_DIFF_SUMMARY) as mock_llm:
            summarize_diff(small_diff)
        user_content = mock_llm.call_args[0][0][1]["content"]
        assert "truncated" not in user_content
        assert small_diff in user_content


# ---------------------------------------------------------------------------
# Retry on invalid response
# ---------------------------------------------------------------------------

class TestRetryOnInvalidResponse:
    def test_retries_on_validation_error(self):
        invalid = {"change_summary": "ok"}  # missing required fields
        call_count = 0

        def side_effect(messages, **kwargs):
            nonlocal call_count
            call_count += 1
            return invalid if call_count == 1 else STEP2_DIFF_SUMMARY

        with _patch_llm_side_effect(side_effect):
            result = summarize_diff("diff text")

        assert call_count == 2
        assert isinstance(result, DiffSummaryOutput)

    def test_raises_after_all_retries_exhausted(self):
        invalid = {"change_summary": "ok"}  # always invalid
        with _patch_llm(invalid):
            with pytest.raises(RuntimeError, match="Could not summarise"):
                summarize_diff("diff text")

    def test_no_real_api_call_made(self):
        with _patch_llm(STEP2_DIFF_SUMMARY):
            result = summarize_diff("diff --git a/x b/x\n+line")
        assert isinstance(result, DiffSummaryOutput)
