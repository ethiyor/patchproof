from __future__ import annotations

import pytest
from pydantic import ValidationError

from models.llm_outputs import (
    DiffSummaryOutput,
    FinalReportSections,
    RequirementsOutput,
    RiskAssessmentOutput,
    RiskFinding,
    VerificationResult,
)
from tests.mocks.llm_responses import (
    STEP1_REQUIREMENTS,
    STEP2_DIFF_SUMMARY,
    STEP3_MISSING,
    STEP3_PARTIAL,
    STEP3_SATISFIED,
    STEP4_RISKS,
    STEP5_REPORT_SECTIONS,
)

# ---------------------------------------------------------------------------
# RequirementsOutput (Step 1)
# ---------------------------------------------------------------------------


class TestRequirementsOutput:
    def test_accepts_valid_fixture(self):
        obj = RequirementsOutput(**STEP1_REQUIREMENTS)
        assert obj.goal == STEP1_REQUIREMENTS["goal"]
        assert len(obj.requirements) == len(STEP1_REQUIREMENTS["requirements"])

    def test_missing_goal_raises(self):
        data = {**STEP1_REQUIREMENTS, "goal": None}
        with pytest.raises(ValidationError):
            RequirementsOutput(**data)

    def test_requirements_must_be_list(self):
        data = {**STEP1_REQUIREMENTS, "requirements": "not a list"}
        with pytest.raises(ValidationError):
            RequirementsOutput(**data)

    def test_empty_requirements_is_allowed(self):
        # An empty list is valid — the pipeline handles it upstream
        data = {**STEP1_REQUIREMENTS, "requirements": []}
        obj = RequirementsOutput(**data)
        assert obj.requirements == []

    def test_risk_domains_is_list_of_strings(self):
        obj = RequirementsOutput(**STEP1_REQUIREMENTS)
        assert all(isinstance(d, str) for d in obj.risk_domains)


# ---------------------------------------------------------------------------
# DiffSummaryOutput (Step 2)
# ---------------------------------------------------------------------------


class TestDiffSummaryOutput:
    def test_accepts_valid_fixture(self):
        obj = DiffSummaryOutput(**STEP2_DIFF_SUMMARY)
        assert obj.change_summary == STEP2_DIFF_SUMMARY["change_summary"]

    def test_unrelated_changes_defaults_to_empty_list(self):
        data = {
            "change_summary": "Added upload endpoint.",
            "implemented_areas": ["backend/routes/upload.py — new route"],
            "possible_side_effects": [],
            "unrelated_changes": [],
        }
        obj = DiffSummaryOutput(**data)
        assert obj.unrelated_changes == []

    def test_missing_change_summary_raises(self):
        data = {**STEP2_DIFF_SUMMARY}
        del data["change_summary"]
        with pytest.raises(ValidationError):
            DiffSummaryOutput(**data)


# ---------------------------------------------------------------------------
# VerificationResult (Step 3)
# ---------------------------------------------------------------------------


class TestVerificationResult:
    def test_accepts_satisfied_with_evidence(self):
        obj = VerificationResult(**STEP3_SATISFIED)
        assert obj.status == "satisfied"
        assert len(obj.evidence) > 0

    def test_accepts_missing_with_no_evidence(self):
        obj = VerificationResult(**STEP3_MISSING)
        assert obj.status == "missing"
        assert obj.evidence == []

    def test_accepts_partially_satisfied_with_evidence(self):
        obj = VerificationResult(**STEP3_PARTIAL)
        assert obj.status == "partially_satisfied"

    def test_satisfied_without_evidence_raises(self):
        """The core evidence rule: satisfied status requires proof."""
        data = {**STEP3_SATISFIED, "evidence": []}
        with pytest.raises(ValidationError, match="evidence"):
            VerificationResult(**data)

    def test_partially_satisfied_without_evidence_raises(self):
        data = {**STEP3_PARTIAL, "evidence": []}
        with pytest.raises(ValidationError, match="evidence"):
            VerificationResult(**data)

    def test_unclear_without_evidence_is_allowed(self):
        data = {
            "requirement": "Add file size validation",
            "status": "unclear",
            "evidence": [],
            "reason": "The diff is ambiguous — cannot determine if validation is present.",
        }
        obj = VerificationResult(**data)
        assert obj.status == "unclear"

    def test_missing_without_evidence_is_allowed(self):
        obj = VerificationResult(**STEP3_MISSING)
        assert obj.status == "missing"

    def test_invalid_status_raises(self):
        data = {**STEP3_SATISFIED, "status": "done"}
        with pytest.raises(ValidationError):
            VerificationResult(**data)

    def test_all_valid_statuses_accepted(self):
        base = {
            "requirement": "req",
            "evidence": ["file.py:1 — found"],
            "reason": "reason",
        }
        for status in ("satisfied", "partially_satisfied"):
            obj = VerificationResult(**{**base, "status": status})
            assert obj.status == status

        no_evidence_base = {**base, "evidence": []}
        for status in ("missing", "unclear", "out_of_scope_change"):
            obj = VerificationResult(**{**no_evidence_base, "status": status})
            assert obj.status == status


# ---------------------------------------------------------------------------
# RiskFinding and RiskAssessmentOutput (Step 4)
# ---------------------------------------------------------------------------


class TestRiskFinding:
    def test_accepts_valid_fixture(self):
        finding = RiskFinding(**STEP4_RISKS["risks"][0])
        assert finding.category == "security"
        assert finding.severity == "error"

    def test_file_path_can_be_none(self):
        finding = RiskFinding(**STEP4_RISKS["risks"][1])
        assert finding.file_path is None

    def test_invalid_category_raises(self):
        data = {**STEP4_RISKS["risks"][0], "category": "unknown_category"}
        with pytest.raises(ValidationError):
            RiskFinding(**data)

    def test_invalid_severity_raises(self):
        data = {**STEP4_RISKS["risks"][0], "severity": "catastrophic"}
        with pytest.raises(ValidationError):
            RiskFinding(**data)


class TestRiskAssessmentOutput:
    def test_accepts_valid_fixture(self):
        obj = RiskAssessmentOutput(**STEP4_RISKS)
        assert len(obj.risks) == 2

    def test_empty_risks_is_valid(self):
        obj = RiskAssessmentOutput(risks=[])
        assert obj.risks == []

    def test_risks_must_be_list(self):
        with pytest.raises(ValidationError):
            RiskAssessmentOutput(risks="not a list")


# ---------------------------------------------------------------------------
# FinalReportSections (Step 5)
# ---------------------------------------------------------------------------


class TestFinalReportSections:
    def test_accepts_valid_fixture(self):
        obj = FinalReportSections(**STEP5_REPORT_SECTIONS)
        assert obj.merge_recommendation == "needs_changes"

    def test_invalid_merge_recommendation_raises(self):
        data = {**STEP5_REPORT_SECTIONS, "merge_recommendation": "maybe"}
        with pytest.raises(ValidationError):
            FinalReportSections(**data)

    def test_all_valid_recommendations_accepted(self):
        base = {
            "executive_summary": "summary",
            "suggested_fixes": [],
        }
        for rec in ("ready", "ready_with_comments", "needs_changes", "do_not_merge"):
            obj = FinalReportSections(**{**base, "merge_recommendation": rec})
            assert obj.merge_recommendation == rec

    def test_suggested_fixes_is_list(self):
        obj = FinalReportSections(**STEP5_REPORT_SECTIONS)
        assert isinstance(obj.suggested_fixes, list)
