from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from core.task_analyzer import analyze_task
from models.llm_outputs import RequirementsOutput
from tests.mocks.llm_responses import STEP1_REQUIREMENTS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_llm(return_value: dict):
    """Patch call_llm in core.task_analyzer to return return_value."""
    return patch("core.task_analyzer.call_llm", return_value=return_value)


def _patch_llm_side_effect(side_effect):
    """Patch call_llm to raise/return a sequence or exception."""
    return patch("core.task_analyzer.call_llm", side_effect=side_effect)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestAnalyzeTaskSuccess:
    def test_returns_requirements_output(self):
        with _patch_llm(STEP1_REQUIREMENTS):
            result = analyze_task("Add PDF upload support with MIME validation.")
        assert isinstance(result, RequirementsOutput)

    def test_goal_is_populated(self):
        with _patch_llm(STEP1_REQUIREMENTS):
            result = analyze_task("Add PDF upload support.")
        assert result.goal == STEP1_REQUIREMENTS["goal"]

    def test_requirements_list_is_returned(self):
        with _patch_llm(STEP1_REQUIREMENTS):
            result = analyze_task("Add PDF upload support.")
        assert len(result.requirements) == len(STEP1_REQUIREMENTS["requirements"])

    def test_expected_test_cases_returned(self):
        with _patch_llm(STEP1_REQUIREMENTS):
            result = analyze_task("Add PDF upload support.")
        assert len(result.expected_test_cases) > 0

    def test_risk_domains_returned(self):
        with _patch_llm(STEP1_REQUIREMENTS):
            result = analyze_task("Add PDF upload support.")
        assert "file_upload" in result.risk_domains

    def test_call_llm_receives_step1_system_prompt(self):
        with patch("core.task_analyzer.call_llm", return_value=STEP1_REQUIREMENTS) as mock_llm:
            analyze_task("Add PDF upload support.")
        messages = mock_llm.call_args[0][0]
        assert messages[0]["role"] == "system"
        assert "requirements" in messages[0]["content"].lower()

    def test_call_llm_receives_task_in_user_message(self):
        task = "Add PDF upload support with MIME validation."
        with patch("core.task_analyzer.call_llm", return_value=STEP1_REQUIREMENTS) as mock_llm:
            analyze_task(task)
        messages = mock_llm.call_args[0][0]
        assert messages[1]["role"] == "user"
        assert task in messages[1]["content"]


# ---------------------------------------------------------------------------
# Retry on empty requirements
# ---------------------------------------------------------------------------


class TestRetryOnEmptyRequirements:
    def test_retries_when_requirements_empty(self):
        empty_response = {**STEP1_REQUIREMENTS, "requirements": []}
        call_count = 0

        def side_effect(messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return empty_response
            return STEP1_REQUIREMENTS

        with _patch_llm_side_effect(side_effect):
            result = analyze_task("Add PDF upload support.")

        assert call_count == 2
        assert len(result.requirements) > 0

    def test_raises_after_all_retries_with_empty_requirements(self):
        empty = {**STEP1_REQUIREMENTS, "requirements": []}
        with _patch_llm(empty):
            with pytest.raises(RuntimeError, match="Could not extract requirements"):
                analyze_task("Add PDF upload support.")

    def test_error_message_mentions_task_description(self):
        empty = {**STEP1_REQUIREMENTS, "requirements": []}
        with _patch_llm(empty):
            with pytest.raises(RuntimeError) as exc_info:
                analyze_task("x")
        assert "task" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Retry on invalid LLM output
# ---------------------------------------------------------------------------


class TestRetryOnInvalidOutput:
    def test_retries_on_validation_error(self):
        """If the first LLM response is invalid, it retries with the same prompt."""
        invalid = {"goal": "ok"}  # missing required fields
        call_count = 0

        def side_effect(messages, **kwargs):
            nonlocal call_count
            call_count += 1
            return invalid if call_count == 1 else STEP1_REQUIREMENTS

        with _patch_llm_side_effect(side_effect):
            result = analyze_task("Add PDF upload support.")

        assert call_count == 2
        assert isinstance(result, RequirementsOutput)

    def test_raises_after_all_retries_with_invalid_output(self):
        invalid = {"goal": "ok"}  # always invalid
        with _patch_llm(invalid):
            with pytest.raises(RuntimeError, match="Could not extract requirements"):
                analyze_task("Add PDF upload support.")

    def test_no_real_api_call_made(self):
        """The mock intercepts call_llm — openai SDK is never touched."""
        import openai
        with _patch_llm(STEP1_REQUIREMENTS):
            # If openai were called, it would fail because no API key is set in test env
            result = analyze_task("Add PDF upload support.")
        assert isinstance(result, RequirementsOutput)
