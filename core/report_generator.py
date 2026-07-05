from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from models.diff_models import ParsedDiff
from models.risk_models import RiskScore

if TYPE_CHECKING:
    from llm.pipeline import PipelineResult

# ---------------------------------------------------------------------------
# Icon maps
# ---------------------------------------------------------------------------

_RISK_EMOJI = {
    "low": "🟢",
    "medium": "🟡",
    "high": "🔴",
    "critical": "🚨",
}

_STATUS_ICON = {
    "satisfied": "✅",
    "partially_satisfied": "⚠️",
    "missing": "❌",
    "unclear": "❓",
    "out_of_scope_change": "🔄",
}

_RECOMMENDATION_LABEL = {
    "ready": "✅ Ready to merge",
    "ready_with_comments": "✅ Ready with minor comments",
    "needs_changes": "⚠️ Needs changes",
    "do_not_merge": "🚫 Do not merge",
}

_SEVERITY_ICON = {
    "info": "ℹ️",
    "warning": "⚠️",
    "error": "🔴",
    "critical": "🚨",
}


def _emoji(level: str) -> str:
    return _RISK_EMOJI.get(level, "")


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def generate_report(
    diff: ParsedDiff,
    risk: RiskScore,
    task_text: str,
    repo_name: str,
    branch: str,
    generated_at: str | None = None,
) -> str:
    """
    Build the Phase 1 Markdown report from a parsed diff and risk score.

    ``generated_at`` defaults to the current UTC time. Pass a fixed string
    in tests to make the output deterministic.
    """
    ts = generated_at or _now_utc()
    emoji = _emoji(risk.level)
    lines: list[str] = []

    # ---- header ------------------------------------------------------------
    lines += [
        "# PatchProof Report",
        "",
        f"**Repository:** {repo_name}  ",
        f"**Branch:** {branch}  ",
        f"**Task:** {task_text}  ",
        f"**Generated:** {ts}  ",
        "",
        "---",
        "",
    ]

    # ---- merge readiness ---------------------------------------------------
    lines += [
        "## Merge Readiness",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Risk score | {risk.score} |",
        f"| Risk level | {emoji} {risk.level.capitalize()} |",
        "",
        "---",
        "",
    ]

    # ---- risk reasons -------------------------------------------------------
    lines += ["## Risk Score Details", ""]
    if risk.reasons:
        lines.append("**Reasons:**")
        lines.append("")
        for reason in risk.reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("No risk factors detected.")
    lines += ["", "---", ""]

    # ---- risky files --------------------------------------------------------
    lines += ["## Risky Files", ""]
    risky = [f for f in diff.files if f.risk_flags]
    if risky:
        lines += ["| File | Risk flags |", "|---|---|"]
        for f in risky:
            lines.append(f"| `{f.path}` | {', '.join(f.risk_flags)} |")
    else:
        lines.append("No risky files detected.")
    lines += ["", "---", ""]

    # ---- changed files summary ----------------------------------------------
    lines += ["## Changed Files", ""]
    if diff.files:
        lines += [
            "| File | Status | Language | +Added | -Removed |",
            "|---|---|---|---|---|",
        ]
        for f in diff.files:
            lang = f.language or "—"
            lines.append(
                f"| `{f.path}` | {f.status} | {lang} | +{f.additions} | -{f.deletions} |"
            )
        lines.append(
            f"| **Total** | | | **+{diff.total_additions}** | **-{diff.total_deletions}** |"
        )
    else:
        lines.append("No files changed.")
    lines += ["", "---", ""]

    # ---- LLM placeholders ---------------------------------------------------
    lines += [
        "## Task Completion Checklist",
        "",
        "> ⚠️ LLM analysis coming in Phase 2. This section will verify each requirement against the diff.",
        "",
        "---",
        "",
        "## Missing Tests",
        "",
        "> ⚠️ LLM analysis coming in Phase 2. This section will list expected test cases not found in the diff.",
        "",
        "---",
        "",
        "## Final Recommendation",
        "",
        "> ⚠️ LLM analysis coming in Phase 2. This section will give a merge recommendation with evidence.",
    ]

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def write_report(
    diff: ParsedDiff,
    risk: RiskScore,
    task_text: str,
    repo_name: str,
    branch: str,
    output: Path,
    generated_at: str | None = None,
) -> str:
    """Generate the Phase 1 report, write it to *output*, return the Markdown string."""
    report = generate_report(diff, risk, task_text, repo_name, branch, generated_at)
    output.write_text(report, encoding="utf-8")
    return report


# ---------------------------------------------------------------------------
# Phase 2 — full LLM-augmented report
# ---------------------------------------------------------------------------

def generate_full_report(
    diff: ParsedDiff,
    risk: RiskScore,
    task_text: str,
    repo_name: str,
    branch: str,
    pipeline_result: "PipelineResult",
    generated_at: str | None = None,
) -> str:
    """
    Build the full Phase 2 Markdown report using all LLM pipeline outputs.

    Sections:
      1.  Header
      2.  Executive Summary        (LLM Step 5)
      3.  Merge Readiness          (rule-based + LLM recommendation)
      4.  Task Completion Checklist (LLM Step 3)
      5.  Risk Score Details        (rule-based)
      6.  Risky Files               (diff parser)
      7.  Missing Tests             (heuristic test checker)
      8.  Possible Bugs & Risks     (LLM Step 4)
      9.  Changed Files             (diff parser)
      10. Suggested Fixes           (LLM Step 5)
      11. Final Recommendation      (LLM Step 5)
    """
    ts = generated_at or _now_utc()
    risk_emoji = _emoji(risk.level)
    pr = pipeline_result
    lines: list[str] = []

    # ---- 1. Header ----------------------------------------------------------
    lines += [
        "# PatchProof Report",
        "",
        f"**Repository:** {repo_name}  ",
        f"**Branch:** {branch}  ",
        f"**Task:** {task_text}  ",
        f"**Generated:** {ts}  ",
        "",
        "---",
        "",
    ]

    # ---- 2. Executive Summary -----------------------------------------------
    lines += [
        "## Executive Summary",
        "",
        pr.report_sections.executive_summary,
        "",
        "---",
        "",
    ]

    # ---- 3. Merge Readiness -------------------------------------------------
    rec = pr.report_sections.merge_recommendation
    rec_label = _RECOMMENDATION_LABEL.get(rec, rec)
    lines += [
        "## Merge Readiness",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Risk score | {risk.score} ({risk_emoji} {risk.level.capitalize()}) |",
        f"| Recommendation | {rec_label} |",
        "",
        "---",
        "",
    ]

    # ---- 4. Task Completion Checklist ---------------------------------------
    lines += ["## Task Completion Checklist", ""]
    if pr.verification_results:
        lines += [
            "| Requirement | Status | Evidence |",
            "|---|---|---|",
        ]
        for vr in pr.verification_results:
            icon = _STATUS_ICON.get(vr.status, "")
            evidence_str = "; ".join(vr.evidence) if vr.evidence else vr.reason[:80]
            lines.append(
                f"| {vr.requirement} | {icon} {vr.status.replace('_', ' ').title()} | {evidence_str} |"
            )
    else:
        lines.append("No requirements were extracted from the task.")
    lines += ["", "---", ""]

    # ---- 5. Risk Score Details ----------------------------------------------
    lines += ["## Risk Score Details", ""]
    if risk.reasons:
        lines.append("**Reasons:**")
        lines.append("")
        for reason in risk.reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("No risk factors detected.")
    lines += ["", "---", ""]

    # ---- 6. Risky Files -----------------------------------------------------
    lines += ["## Risky Files", ""]
    risky = [f for f in diff.files if f.risk_flags]
    if risky:
        lines += ["| File | Risk flags |", "|---|---|"]
        for f in risky:
            lines.append(f"| `{f.path}` | {', '.join(f.risk_flags)} |")
    else:
        lines.append("No risky files detected.")
    lines += ["", "---", ""]

    # ---- 7. Missing Tests ---------------------------------------------------
    lines += ["## Missing Tests", ""]
    if pr.test_results:
        for tr in pr.test_results:
            checkbox = "[x]" if tr.status == "present" else "[ ]"
            lines.append(f"- {checkbox} {tr.test_case}")
    else:
        lines.append("No expected test cases were identified.")
    lines += ["", "---", ""]

    # ---- 8. Possible Bugs & Risks -------------------------------------------
    lines += ["## Possible Bugs & Risks", ""]
    if pr.risk_assessment.risks:
        for finding in pr.risk_assessment.risks:
            sev_icon = _SEVERITY_ICON.get(finding.severity, "")
            file_ref = f" — `{finding.file_path}`" if finding.file_path else ""
            lines += [
                f"**{sev_icon} {finding.title}**{file_ref}",
                "",
                finding.description,
                "",
                f"> Evidence: {finding.evidence}",
                "",
            ]
    else:
        lines.append("No specific bugs or risks identified by the LLM.")
    lines += ["---", ""]

    # ---- 9. Changed Files ---------------------------------------------------
    lines += ["## Changed Files", ""]
    if diff.files:
        lines += [
            "| File | Status | Language | +Added | -Removed |",
            "|---|---|---|---|---|",
        ]
        for f in diff.files:
            lang = f.language or "—"
            lines.append(
                f"| `{f.path}` | {f.status} | {lang} | +{f.additions} | -{f.deletions} |"
            )
        lines.append(
            f"| **Total** | | | **+{diff.total_additions}** | **-{diff.total_deletions}** |"
        )
    else:
        lines.append("No files changed.")
    lines += ["", "---", ""]

    # ---- 10. Suggested Fixes ------------------------------------------------
    lines += ["## Suggested Fixes", ""]
    if pr.report_sections.suggested_fixes:
        for fix in pr.report_sections.suggested_fixes:
            lines.append(f"- {fix}")
    else:
        lines.append("No specific fixes suggested.")
    lines += ["", "---", ""]

    # ---- 11. Final Recommendation -------------------------------------------
    lines += [
        "## Final Recommendation",
        "",
        f"> **{rec_label}**",
    ]

    return "\n".join(lines) + "\n"


def write_full_report(
    diff: ParsedDiff,
    risk: RiskScore,
    task_text: str,
    repo_name: str,
    branch: str,
    pipeline_result: "PipelineResult",
    output: Path,
    generated_at: str | None = None,
) -> str:
    """Generate the full Phase 2 report, write it to *output*, return the Markdown."""
    report = generate_full_report(
        diff, risk, task_text, repo_name, branch, pipeline_result, generated_at
    )
    output.write_text(report, encoding="utf-8")
    return report
