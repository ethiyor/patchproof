from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from core.diff_parser import parse_diff
from core.risk_scorer import compute_risk
from core.report_generator import generate_full_report, write_full_report
from core.test_checker import TestCaseResult
from models.diff_models import ParsedDiff, ParsedFile
from models.llm_outputs import (
    DiffSummaryOutput,
    FinalReportSections,
    RequirementsOutput,
    RiskAssessmentOutput,
    VerificationResult,
)
from models.risk_models import RiskScore
from tests.mocks.llm_responses import (
    STEP1_REQUIREMENTS,
    STEP2_DIFF_SUMMARY,
    STEP3_SATISFIED,
    STEP3_MISSING,
    STEP4_RISKS,
    STEP5_REPORT_SECTIONS,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample_diffs"

_FIXED_TS = "2026-07-05 00:00 UTC"


# ---------------------------------------------------------------------------
# Build a realistic PipelineResult from mock data
# ---------------------------------------------------------------------------

def _make_pipeline_result():
    """Build a PipelineResult using the mock fixtures."""
    from llm.pipeline import PipelineResult

    return PipelineResult(
        requirements=RequirementsOutput(**STEP1_REQUIREMENTS),
        diff_summary=DiffSummaryOutput(**STEP2_DIFF_SUMMARY),
        verification_results=[
            VerificationResult(**STEP3_SATISFIED),
            VerificationResult(**STEP3_MISSING),
        ],
        risk_assessment=RiskAssessmentOutput(**STEP4_RISKS),
        test_results=[
            TestCaseResult(test_case="valid PDF upload returns 200", status="missing"),
            TestCaseResult(test_case="invalid MIME rejected with 400", status="missing"),
        ],
        report_sections=FinalReportSections(**STEP5_REPORT_SECTIONS),
    )


def _auth_diff_and_risk():
    raw = (FIXTURES / "auth_change.diff").read_text()
    diff = parse_diff(raw)
    risk = compute_risk(diff)
    return diff, risk


# ---------------------------------------------------------------------------
# Section presence
# ---------------------------------------------------------------------------

class TestFullReportSections:
    def setup_method(self):
        diff, risk = _auth_diff_and_risk()
        pr = _make_pipeline_result()
        self.report = generate_full_report(
            diff=diff, risk=risk,
            task_text="Update JWT token expiry and add IAT claim.",
            repo_name="test-repo", branch="test-branch",
            pipeline_result=pr,
            generated_at=_FIXED_TS,
        )

    def test_has_title(self):
        assert "# PatchProof Report" in self.report

    def test_has_executive_summary(self):
        assert "## Executive Summary" in self.report
        assert STEP5_REPORT_SECTIONS["executive_summary"] in self.report

    def test_has_merge_readiness(self):
        assert "## Merge Readiness" in self.report

    def test_has_task_completion_checklist(self):
        assert "## Task Completion Checklist" in self.report

    def test_satisfied_requirement_has_check_icon(self):
        assert "✅" in self.report

    def test_missing_requirement_has_x_icon(self):
        assert "❌" in self.report

    def test_has_risk_score_section(self):
        assert "## Risk Score Details" in self.report

    def test_has_risky_files_section(self):
        assert "## Risky Files" in self.report

    def test_has_missing_tests_section(self):
        assert "## Missing Tests" in self.report
        assert "valid PDF upload returns 200" in self.report

    def test_has_possible_bugs_section(self):
        assert "## Possible Bugs" in self.report
        assert "No file size limit" in self.report

    def test_has_changed_files_section(self):
        assert "## Changed Files" in self.report

    def test_has_suggested_fixes(self):
        assert "## Suggested Fixes" in self.report
        assert STEP5_REPORT_SECTIONS["suggested_fixes"][0] in self.report

    def test_has_final_recommendation(self):
        assert "## Final Recommendation" in self.report
        assert "Needs changes" in self.report

    def test_recommendation_label_is_human_readable(self):
        # "needs_changes" should be rendered as "Needs changes" not the raw enum value
        assert "needs_changes" not in self.report.split("## Final")[1]

    def test_ends_with_newline(self):
        assert self.report.endswith("\n")

    def test_no_phase_2_placeholders(self):
        assert "LLM analysis coming in Phase 2" not in self.report


# ---------------------------------------------------------------------------
# Missing test checkbox markers
# ---------------------------------------------------------------------------

class TestMissingTestsSection:
    def test_missing_cases_use_empty_checkbox(self):
        diff, risk = _auth_diff_and_risk()
        pr = _make_pipeline_result()
        report = generate_full_report(
            diff, risk, "task", "repo", "main", pr, _FIXED_TS
        )
        assert "- [ ]" in report

    def test_present_cases_use_checked_checkbox(self):
        diff, risk = _auth_diff_and_risk()
        from llm.pipeline import PipelineResult
        pr = _make_pipeline_result()
        # Override test_results with one present case
        pr = PipelineResult(
            requirements=pr.requirements,
            diff_summary=pr.diff_summary,
            verification_results=pr.verification_results,
            risk_assessment=pr.risk_assessment,
            test_results=[
                TestCaseResult(test_case="valid upload works", status="present"),
            ],
            report_sections=pr.report_sections,
        )
        report = generate_full_report(diff, risk, "task", "repo", "main", pr, _FIXED_TS)
        assert "- [x]" in report


# ---------------------------------------------------------------------------
# write_full_report
# ---------------------------------------------------------------------------

class TestWriteFullReport:
    def test_creates_file(self, tmp_path):
        diff, risk = _auth_diff_and_risk()
        pr = _make_pipeline_result()
        out = tmp_path / "patchproof-report.md"
        write_full_report(diff, risk, "task", "repo", "main", pr, out, _FIXED_TS)
        assert out.exists()

    def test_file_content_matches_return_value(self, tmp_path):
        diff, risk = _auth_diff_and_risk()
        pr = _make_pipeline_result()
        out = tmp_path / "patchproof-report.md"
        returned = write_full_report(diff, risk, "task", "repo", "main", pr, out, _FIXED_TS)
        assert out.read_text(encoding="utf-8") == returned


# ---------------------------------------------------------------------------
# run_pipeline (integration, all LLM calls mocked)
# ---------------------------------------------------------------------------

class TestRunPipeline:
    def _mock_llm(self, step: int) -> dict:
        mapping = {
            1: STEP1_REQUIREMENTS,
            2: STEP2_DIFF_SUMMARY,
            3: STEP3_SATISFIED,
            4: STEP4_RISKS,
            5: STEP5_REPORT_SECTIONS,
        }
        return mapping[step]

    def test_returns_pipeline_result(self):
        from llm.pipeline import run_pipeline, PipelineResult

        raw = (FIXTURES / "auth_change.diff").read_text()
        diff = parse_diff(raw)
        risk = compute_risk(diff)

        call_count = [0]
        responses = [
            STEP1_REQUIREMENTS,
            STEP2_DIFF_SUMMARY,
            STEP3_SATISFIED,   # one requirement
            STEP4_RISKS,
            STEP5_REPORT_SECTIONS,
        ]

        def mock_call_llm(messages, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            return responses[min(idx, len(responses) - 1)]

        with patch("core.task_analyzer.call_llm", side_effect=mock_call_llm), \
             patch("core.diff_summarizer.call_llm", side_effect=mock_call_llm), \
             patch("core.verification_engine.call_llm", side_effect=mock_call_llm), \
             patch("llm.pipeline.call_llm", side_effect=mock_call_llm):
            result = run_pipeline("Update JWT token expiry.", raw, diff, risk)

        assert isinstance(result, PipelineResult)
        assert isinstance(result.requirements, RequirementsOutput)
        assert isinstance(result.diff_summary, DiffSummaryOutput)
        assert isinstance(result.risk_assessment, RiskAssessmentOutput)
        assert isinstance(result.report_sections, FinalReportSections)

    def test_pipeline_result_feeds_full_report(self):
        """End-to-end: pipeline result → generate_full_report → has all sections."""
        from llm.pipeline import run_pipeline

        raw = (FIXTURES / "auth_change.diff").read_text()
        diff = parse_diff(raw)
        risk = compute_risk(diff)

        def mock_llm(messages, **kwargs):
            content = messages[0]["content"].lower()
            if "requirements analyst" in content:
                return STEP1_REQUIREMENTS
            if "code change analyst" in content:
                return STEP2_DIFF_SUMMARY
            if "code reviewer" in content:
                return STEP3_SATISFIED
            if "security and quality" in content:
                return STEP4_RISKS
            return STEP5_REPORT_SECTIONS

        with patch("core.task_analyzer.call_llm", side_effect=mock_llm), \
             patch("core.diff_summarizer.call_llm", side_effect=mock_llm), \
             patch("core.verification_engine.call_llm", side_effect=mock_llm), \
             patch("llm.pipeline.call_llm", side_effect=mock_llm):
            result = run_pipeline("Update JWT token expiry.", raw, diff, risk)

        report = generate_full_report(diff, risk, "task", "repo", "main", result, _FIXED_TS)

        for section in [
            "## Executive Summary",
            "## Task Completion Checklist",
            "## Missing Tests",
            "## Possible Bugs",
            "## Suggested Fixes",
            "## Final Recommendation",
        ]:
            assert section in report, f"Missing section: {section}"
