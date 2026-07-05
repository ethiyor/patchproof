from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

VerificationStatus = Literal[
    "satisfied",
    "partially_satisfied",
    "missing",
    "unclear",
    "out_of_scope_change",
]

FindingCategory = Literal[
    "task_alignment",
    "missing_test",
    "security",
    "database",
    "api_contract",
    "config",
    "dependency",
    "bug_risk",
    "out_of_scope",
]

FindingSeverity = Literal["info", "warning", "error", "critical"]

MergeRecommendation = Literal[
    "ready",
    "ready_with_comments",
    "needs_changes",
    "do_not_merge",
]

# ---------------------------------------------------------------------------
# Step 1 — RequirementsOutput
# ---------------------------------------------------------------------------


class RequirementsOutput(BaseModel):
    """Output of LLM Step 1: requirement extraction from a task description."""

    goal: Annotated[
        str,
        Field(description="One-sentence summary of the overall task goal."),
    ]
    requirements: Annotated[
        list[str],
        Field(
            description=(
                "Concrete, checkable requirements extracted from the task. "
                "Each item should describe one specific thing that must be implemented."
            )
        ),
    ]
    expected_test_cases: Annotated[
        list[str],
        Field(
            description=(
                "Test cases that should exist to verify this task. "
                "Include success paths, failure paths, and edge cases."
            )
        ),
    ]
    risk_domains: Annotated[
        list[str],
        Field(
            description=(
                "Risk domains relevant to this task. "
                "Examples: file_upload, auth, database, payments, storage, security."
            )
        ),
    ]


# ---------------------------------------------------------------------------
# Step 2 — DiffSummaryOutput
# ---------------------------------------------------------------------------


class DiffSummaryOutput(BaseModel):
    """Output of LLM Step 2: diff summarisation."""

    change_summary: Annotated[
        str,
        Field(
            description=(
                "One or two sentences describing what changed overall. "
                "Reference specific file paths where relevant."
            )
        ),
    ]
    implemented_areas: Annotated[
        list[str],
        Field(
            description=(
                "Areas of the codebase that were implemented or modified. "
                "Format each item as 'path/to/file.py — description of change'."
            )
        ),
    ]
    possible_side_effects: Annotated[
        list[str],
        Field(
            description=(
                "Unintended or implicit consequences of the changes "
                "(e.g. schema changes, new external dependencies, changed API contracts)."
            )
        ),
    ]
    unrelated_changes: Annotated[
        list[str],
        Field(
            description=(
                "Files or changes that appear unrelated to the stated task goal. "
                "Return an empty list if all changes are relevant."
            )
        ),
    ]


# ---------------------------------------------------------------------------
# Step 3 — VerificationResult
# ---------------------------------------------------------------------------


class VerificationResult(BaseModel):
    """Output of LLM Step 3: per-requirement verification against the diff."""

    requirement: Annotated[
        str,
        Field(description="The exact requirement text being verified."),
    ]
    status: Annotated[
        VerificationStatus,
        Field(
            description=(
                "satisfied — clear evidence the requirement is fully implemented. "
                "partially_satisfied — some but not all aspects covered. "
                "missing — no evidence of implementation in the diff. "
                "unclear — diff is ambiguous or context is insufficient. "
                "out_of_scope_change — unrelated change was made instead."
            )
        ),
    ]
    evidence: Annotated[
        list[str],
        Field(
            description=(
                "File:line citations that support this status. "
                "Required when status is 'satisfied' or 'partially_satisfied'. "
                "Format: 'path/to/file.py:42 — brief description'."
            )
        ),
    ]
    reason: Annotated[
        str,
        Field(
            description=(
                "Explanation of why this status was assigned. "
                "Must reference specific code from the diff, not general assumptions."
            )
        ),
    ]

    @model_validator(mode="after")
    def _evidence_required_when_satisfied(self) -> "VerificationResult":
        """
        Enforce the evidence rule: any positive status (satisfied /
        partially_satisfied) must cite at least one file:line reference.

        This prevents the LLM from claiming something is done without proof.
        """
        if self.status in ("satisfied", "partially_satisfied") and not self.evidence:
            raise ValueError(
                f"status='{self.status}' requires at least one evidence citation. "
                "Add a 'file:line — description' entry to the evidence list, "
                "or downgrade the status to 'unclear' if you cannot find proof."
            )
        return self


# ---------------------------------------------------------------------------
# Step 4 — RiskAssessmentOutput
# ---------------------------------------------------------------------------


class RiskFinding(BaseModel):
    """A single risk finding from LLM Step 4."""

    category: Annotated[
        FindingCategory,
        Field(description="The category this finding belongs to."),
    ]
    severity: Annotated[
        FindingSeverity,
        Field(description="How severe this finding is: info, warning, error, or critical."),
    ]
    title: Annotated[
        str,
        Field(description="Short title for this finding (one line, no period)."),
    ]
    description: Annotated[
        str,
        Field(
            description=(
                "Full explanation of the risk. Must describe the actual problem, "
                "not a general warning."
            )
        ),
    ]
    file_path: Annotated[
        str | None,
        Field(
            default=None,
            description="Path to the file where this issue was found. Null if not file-specific.",
        ),
    ]
    evidence: Annotated[
        str,
        Field(
            description=(
                "Direct quote or reference from the diff that supports this finding. "
                "Be specific — cite the function, variable, or line that is the problem."
            )
        ),
    ]


class RiskAssessmentOutput(BaseModel):
    """Output of LLM Step 4: risk assessment over the full diff."""

    risks: Annotated[
        list[RiskFinding],
        Field(
            description=(
                "List of risk findings. Prefer 2–5 high-confidence findings "
                "over many vague ones. Every finding must have evidence."
            )
        ),
    ]


# ---------------------------------------------------------------------------
# Step 5 — FinalReportSections
# ---------------------------------------------------------------------------


class FinalReportSections(BaseModel):
    """Output of LLM Step 5: the two prose sections of the final report."""

    executive_summary: Annotated[
        str,
        Field(
            description=(
                "2–4 sentences summarising what the AI agent built, what it missed, "
                "and whether the PR is ready to merge. Be direct and specific."
            )
        ),
    ]
    suggested_fixes: Annotated[
        list[str],
        Field(
            description=(
                "Concrete, actionable fixes the developer should make before merging. "
                "Each item should be one specific thing to do."
            )
        ),
    ]
    merge_recommendation: Annotated[
        MergeRecommendation,
        Field(
            description=(
                "ready — all requirements satisfied, risk is low, tests present. "
                "ready_with_comments — minor issues only, safe to merge with notes. "
                "needs_changes — missing requirements or high risk, fix before merging. "
                "do_not_merge — critical risk or security issue present."
            )
        ),
    ]
