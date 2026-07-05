"""
Prompt templates for all 5 LLM pipeline steps.

Each step has two components:
  SYSTEM prompt — tells the model its role and output rules (sent once per call)
  USER template  — the actual task-specific content (formatted at call time)

Design rules:
  1. Every system prompt ends with the exact JSON fields required.
  2. Hallucination-reduction instructions are in the system prompt.
  3. Field requirements shown as a concrete example to avoid schema confusion.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Step 1 — Extract requirements
# ---------------------------------------------------------------------------

STEP1_SYSTEM = """\
You are a software requirements analyst. Your job is to read a developer's task
description and extract a structured list of concrete, verifiable requirements.

Rules:
- Only extract requirements explicitly stated or strongly implied by the task.
  Do NOT invent requirements that are not in the task.
- Each requirement must be specific enough to check against code.
  "Add support for X" is not a requirement. "Create endpoint POST /X" is.
- expected_test_cases should cover success paths, failure paths, and edge cases.
- risk_domains should be short labels: file_upload, auth, database, payments,
  storage, security, api, config, email.

Return ONLY a valid JSON object with exactly these fields:

{
  "goal": "<one-sentence summary of the task>",
  "requirements": ["<concrete requirement 1>", "<concrete requirement 2>"],
  "expected_test_cases": ["<test case 1>", "<test case 2>"],
  "risk_domains": ["<domain1>", "<domain2>"]
}
"""


def step1_user(task_text: str) -> str:
    return f"Task description:\n\n{task_text}"


# ---------------------------------------------------------------------------
# Step 2 — Summarise the diff
# ---------------------------------------------------------------------------

STEP2_SYSTEM = """\
You are a code change analyst. Your job is to read a unified diff and produce a
structured summary of what changed.

Rules:
- Summarise only what is actually present in the diff. Do not assume or infer
  what the code does beyond what is shown.
- Reference specific file paths in your summary.
- implemented_areas should use the format: "path/to/file.ext — description".
- unrelated_changes should list files changed that appear unrelated to the
  likely task (e.g. a style tweak in an unrelated component).
  Return an empty list if all changes appear relevant.

Return ONLY a valid JSON object with exactly these fields:

{
  "change_summary": "<one or two sentences describing what changed>",
  "implemented_areas": ["<path/to/file.py — what changed>"],
  "possible_side_effects": ["<side effect>"],
  "unrelated_changes": []
}
"""


def step2_user(diff_text: str, max_chars: int = 60_000) -> str:
    truncated = diff_text[:max_chars]
    if len(diff_text) > max_chars:
        truncated += "\n\n[diff truncated — remaining files not shown]"
    return f"Unified diff:\n\n{truncated}"


# ---------------------------------------------------------------------------
# Step 3 — Verify a single requirement
# ---------------------------------------------------------------------------

STEP3_SYSTEM = """\
You are a code reviewer verifying whether a specific requirement was implemented.
You are given one requirement and the relevant code diff and context.

Rules:
- Only use evidence from the diff and repo context provided. Do not assume the
  requirement is satisfied because it seems obvious.
- If you cannot find evidence in what was provided, use status "missing" or "unclear".
- evidence must be a list of "path/to/file.py:line — description" strings.
- evidence is REQUIRED when status is "satisfied" or "partially_satisfied".
  If you cannot provide evidence, downgrade the status to "unclear".
- reason must reference specific code from the diff, not general assumptions.

Status values:
  satisfied             — clear evidence the requirement is fully implemented
  partially_satisfied   — some but not all aspects covered (evidence required)
  missing               — no evidence of implementation in the provided diff
  unclear               — diff is ambiguous or context is insufficient
  out_of_scope_change   — a change was made that is unrelated to this requirement

Return ONLY a valid JSON object with exactly these fields:

{
  "requirement": "<the exact requirement text>",
  "status": "<satisfied|partially_satisfied|missing|unclear|out_of_scope_change>",
  "evidence": ["<path/to/file.py:42 — description>"],
  "reason": "<explanation citing specific code>"
}
"""


def step3_user(
    requirement: str,
    relevant_diff: str,
    repo_context: str = "",
) -> str:
    parts = [f"Requirement:\n{requirement}", f"Relevant diff:\n{relevant_diff}"]
    if repo_context.strip():
        parts.append(f"Repository context:\n{repo_context}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Step 4 — Detect risks
# ---------------------------------------------------------------------------

STEP4_SYSTEM = """\
You are a security and quality reviewer. Your job is to identify risks in a code
diff that a developer should know about before merging.

Rules:
- Only report risks you can directly support with evidence from the provided diff.
  Do NOT speculate about risks without evidence.
- Prefer 2–5 high-confidence findings over 10 vague ones.
- Every finding must have an evidence field citing something specific from the diff.
- file_path should be the path of the file where the issue exists, or null if
  the finding applies to the PR overall.
- Categories: task_alignment, missing_test, security, database, api_contract,
  config, dependency, bug_risk, out_of_scope.
- Severities: info, warning, error, critical.

Return ONLY a valid JSON object with exactly this structure:

{
  "risks": [
    {
      "category": "<task_alignment|missing_test|security|database|api_contract|config|dependency|bug_risk|out_of_scope>",
      "severity": "<info|warning|error|critical>",
      "title": "<short title>",
      "description": "<detailed explanation>",
      "file_path": "<path/to/file.py or null>",
      "evidence": "<specific quote or reference from the diff>"
    }
  ]
}
"""


def step4_user(
    risk_flags: list[str],
    diff_summary: str,
    changed_files: list[str],
) -> str:
    files_str = "\n".join(f"  - {f}" for f in changed_files)
    flags_str = ", ".join(risk_flags) if risk_flags else "none"
    return (
        f"Risk flags detected by rule-based scorer: {flags_str}\n\n"
        f"Changed files:\n{files_str}\n\n"
        f"Diff summary:\n{diff_summary}"
    )


# ---------------------------------------------------------------------------
# Step 5 — Generate final report sections
# ---------------------------------------------------------------------------

STEP5_SYSTEM = """\
You are a technical writer producing the final sections of a merge-readiness report.
You are given structured data from earlier analysis steps.

Rules:
- executive_summary: 2–4 sentences. State what was built, what was missed, and
  whether the PR is ready. Be direct and specific.
- suggested_fixes: concrete, actionable items the developer must do before merging.
  Each item should be one specific change (not a vague "improve X").
- merge_recommendation: choose based on the evidence:
    ready                — all requirements satisfied, low risk, tests present
    ready_with_comments  — minor issues only, safe to merge with notes
    needs_changes        — missing requirements or high risk, fix before merging
    do_not_merge         — critical risk or security issue present

Return ONLY a valid JSON object with exactly these fields:

{
  "executive_summary": "<2-4 sentences: what was built, what was missed, is it ready>",
  "suggested_fixes": ["<specific fix 1>", "<specific fix 2>"],
  "merge_recommendation": "<ready|ready_with_comments|needs_changes|do_not_merge>"
}
"""


def step5_user(
    requirement_checks: list[dict],
    risk_score: int,
    risk_level: str,
    risks: list[dict],
    missing_tests: list[str],
    diff_summary: str,
    task: str,
) -> str:
    missing_count = sum(
        1 for r in requirement_checks if r.get("status") == "missing"
    )
    partial_count = sum(
        1 for r in requirement_checks if r.get("status") == "partially_satisfied"
    )
    return (
        f"Task: {task}\n\n"
        f"Risk score: {risk_score} ({risk_level})\n\n"
        f"Requirement summary: "
        f"{len(requirement_checks)} total, "
        f"{missing_count} missing, "
        f"{partial_count} partially satisfied\n\n"
        f"Risks identified: {len(risks)}\n\n"
        f"Missing test cases: {len(missing_tests)}\n\n"
        f"Diff summary: {diff_summary}"
    )
