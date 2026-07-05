from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from models.diff_models import ParsedDiff
from models.risk_models import RiskScore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RISK_EMOJI = {
    "low": "🟢",
    "medium": "🟡",
    "high": "🔴",
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
    """Generate the report, write it to *output*, and return the Markdown string."""
    report = generate_report(diff, risk, task_text, repo_name, branch, generated_at)
    output.write_text(report, encoding="utf-8")
    return report
