from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import ValidationError

from core.diff_summarizer import summarize_diff
from core.task_analyzer import analyze_task
from core.test_checker import TestCaseResult, check_test_adequacy
from core.verification_engine import verify_requirements
from llm.client import call_llm
from llm.prompts import STEP4_SYSTEM, STEP5_SYSTEM, step4_user, step5_user
from models.diff_models import ParsedDiff
from models.llm_outputs import (
    DiffSummaryOutput,
    FinalReportSections,
    RequirementsOutput,
    RiskAssessmentOutput,
    VerificationResult,
)
from models.risk_models import RiskScore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass
class PipelineResult:
    """All structured outputs from the 5-step LLM pipeline."""

    requirements: RequirementsOutput
    diff_summary: DiffSummaryOutput
    verification_results: list[VerificationResult]
    risk_assessment: RiskAssessmentOutput
    test_results: list[TestCaseResult]
    report_sections: FinalReportSections


# ---------------------------------------------------------------------------
# Internal step helpers
# ---------------------------------------------------------------------------


def _assess_risks(
    parsed_diff: ParsedDiff,
    diff_summary: DiffSummaryOutput,
) -> RiskAssessmentOutput:
    """LLM Step 4 — identify risky changes in the diff."""
    all_flags: list[str] = sorted({
        flag
        for f in parsed_diff.files
        for flag in f.risk_flags
    })
    changed_files = [f.path for f in parsed_diff.files]

    messages = [
        {"role": "system", "content": STEP4_SYSTEM},
        {
            "role": "user",
            "content": step4_user(all_flags, diff_summary.change_summary, changed_files),
        },
    ]
    try:
        raw = call_llm(messages)
        return RiskAssessmentOutput(**raw)
    except Exception as exc:
        logger.warning("Step 4 (risk assessment) failed, returning empty: %s", exc)
        return RiskAssessmentOutput(risks=[])


def _generate_sections(
    verification_results: list[VerificationResult],
    risk: RiskScore,
    risk_assessment: RiskAssessmentOutput,
    missing_tests: list[str],
    diff_summary: DiffSummaryOutput,
    task_text: str,
) -> FinalReportSections:
    """LLM Step 5 — write executive summary and suggested fixes."""
    req_checks = [
        {"requirement": r.requirement, "status": r.status}
        for r in verification_results
    ]
    risks_data = [r.model_dump() for r in risk_assessment.risks]

    messages = [
        {"role": "system", "content": STEP5_SYSTEM},
        {
            "role": "user",
            "content": step5_user(
                requirement_checks=req_checks,
                risk_score=risk.score,
                risk_level=risk.level,
                risks=risks_data,
                missing_tests=missing_tests,
                diff_summary=diff_summary.change_summary,
                task=task_text,
            ),
        },
    ]
    try:
        raw = call_llm(messages)
        return FinalReportSections(**raw)
    except Exception as exc:
        logger.warning("Step 5 (report sections) failed, using fallback: %s", exc)
        missing_count = sum(1 for r in verification_results if r.status == "missing")
        rec = "needs_changes" if (risk.score >= 3 or missing_count > 0) else "ready"
        return FinalReportSections(
            executive_summary=(
                "Analysis complete. "
                "See requirement checklist and risk details below."
            ),
            suggested_fixes=[],
            merge_recommendation=rec,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_pipeline(
    task_text: str,
    diff_text: str,
    parsed_diff: ParsedDiff,
    risk: RiskScore,
    max_workers: int = 1,
) -> PipelineResult:
    """
    Run the full 5-step LLM analysis pipeline.

    Steps:
      1. analyze_task    — extract requirements from task description
      2. summarize_diff  — summarise what changed in the diff
      3. verify_requirements — check each requirement against the diff
      4. _assess_risks   — identify risky changes (LLM)
         check_test_adequacy — find missing test cases (heuristic)
      5. _generate_sections — produce executive summary and fixes (LLM)

    Args:
        task_text:    Contents of task.txt.
        diff_text:    Raw unified diff string.
        parsed_diff:  ParsedDiff from parse_diff().
        risk:         RiskScore from compute_risk() (rule-based).
        max_workers:  Parallel workers for Step 3. Default 1 (sequential).

    Returns:
        PipelineResult with all structured outputs.
    """
    logger.info("Pipeline starting: diff=%d chars", len(diff_text))

    # Step 1
    requirements = analyze_task(task_text)
    logger.info("Step 1 done: %d requirements", len(requirements.requirements))

    # Step 2
    try:
        diff_summary = summarize_diff(diff_text)
    except RuntimeError as exc:
        logger.warning("Step 2 failed, using stub summary: %s", exc)
        diff_summary = DiffSummaryOutput(
            change_summary="Diff summarisation failed.",
            implemented_areas=[],
            possible_side_effects=[],
            unrelated_changes=[],
        )
    logger.info("Step 2 done")

    # Step 3
    verification_results = verify_requirements(
        requirements.requirements,
        diff_text,
        max_workers=max_workers,
    )
    logger.info("Step 3 done: %d verifications", len(verification_results))

    # Step 4 (LLM) + test adequacy (heuristic)
    risk_assessment = _assess_risks(parsed_diff, diff_summary)
    test_results = check_test_adequacy(requirements.expected_test_cases, parsed_diff)
    logger.info(
        "Step 4 done: %d risk findings, %d test cases",
        len(risk_assessment.risks),
        len(test_results),
    )

    # Step 5
    missing_tests = [r.test_case for r in test_results if r.status == "missing"]
    report_sections = _generate_sections(
        verification_results=verification_results,
        risk=risk,
        risk_assessment=risk_assessment,
        missing_tests=missing_tests,
        diff_summary=diff_summary,
        task_text=task_text,
    )
    logger.info("Step 5 done: recommendation=%s", report_sections.merge_recommendation)

    return PipelineResult(
        requirements=requirements,
        diff_summary=diff_summary,
        verification_results=verification_results,
        risk_assessment=risk_assessment,
        test_results=test_results,
        report_sections=report_sections,
    )
