# Phase 2 — LLM Pipeline

**Prerequisites:** Phase 1 complete. `patchproof review` writes a basic report.
**Reference docs:** [06_llm_pipeline.md](../06_llm_pipeline.md), [04_architecture.md](../04_architecture.md)

---

## Overview

Add the AI brain. The CLI now uses GPT-4o to extract requirements from the task description, summarize the diff, verify each requirement, check test adequacy, and produce an evidence-based report.

---

## Milestone 2.1 — LLM Client Setup

**Goal:** A reusable, testable OpenAI wrapper with retry and error handling.

**Files to create:**

```
llm/__init__.py
llm/client.py
tests/mocks/llm_responses.py
```

**Tasks:**
- Read `OPENAI_API_KEY` from environment — raise a clear error if missing
- Wrap `openai.chat.completions.create` with:
  - JSON mode enabled (`response_format={"type": "json_object"}`)
  - Temperature 0.1
  - Retry once on malformed JSON or network error
  - Log token usage per call (not the content)
- Never log the API key — only log `OPENAI_API_KEY=sk-****`
- Create `tests/mocks/llm_responses.py` with mock response fixtures for all 5 steps

**Done when:**
- `llm/client.py` makes a real call with `OPENAI_API_KEY` set and returns parsed JSON
- With the mock patched in, no real API call is made in tests

---

## Milestone 2.2 — Pydantic Output Models

**Goal:** Define strict Pydantic models for every LLM response shape before writing any pipeline step.

**Files to create:**

```
models/llm_outputs.py
tests/unit/test_llm_models.py
```

**Tasks:**
- `RequirementsOutput`: `goal`, `requirements`, `expected_test_cases`, `risk_domains`
- `DiffSummaryOutput`: `change_summary`, `implemented_areas`, `possible_side_effects`, `unrelated_changes`
- `VerificationResult`: `requirement`, `status` (enum), `evidence` (list), `reason`
- `RiskAssessmentOutput`: `risks` (list of `RiskFinding`)
- `RiskFinding`: `category`, `severity`, `title`, `description`, `file_path`, `evidence`
- `FinalReportSections`: `executive_summary`, `suggested_fixes`, `merge_recommendation`
- All fields should have `description` annotations for prompt clarity

**Done when:**
- Unit tests verify that valid JSON is accepted and invalid JSON raises `ValidationError`
- A `VerificationResult` with `status="satisfied"` and empty `evidence` raises a validation error

---

## Milestone 2.3 — Task Analyzer (LLM Step 1)

**Goal:** Extract structured requirements from the task description.

**Files to create:**

```
core/task_analyzer.py
llm/prompts.py
tests/unit/test_task_analyzer.py
```

**Tasks:**
- Write the Step 1 prompt in `llm/prompts.py` — see [06_llm_pipeline.md](../06_llm_pipeline.md) for exact input/output
- Call `llm/client.py` and validate the response with `RequirementsOutput`
- Retry once if Pydantic validation fails
- If still invalid, raise a user-facing error: `"Could not extract requirements from task. Try writing a more specific task description."`

**Done when:**
- Given `task.txt` with "Add PDF upload support", returns 4–6 concrete requirements
- Given a vague 3-word task, retry logic fires and a clear error is raised
- Mock-based unit test passes without calling real OpenAI

---

## Milestone 2.4 — Diff Summarizer (LLM Step 2)

**Goal:** Summarize what the diff changed in plain language.

**Files to create:**

```
core/diff_summarizer.py
tests/unit/test_diff_summarizer.py
```

**Tasks:**
- Write the Step 2 prompt in `llm/prompts.py`
- Chunk large diffs: if total diff > 60,000 characters, summarize each file separately and merge
- Validate response with `DiffSummaryOutput`
- Detect `unrelated_changes` — files changed that don't relate to the task

**Done when:**
- Given `simple_add.diff`, returns a `change_summary` that mentions the key files changed
- Mock-based unit test passes

---

## Milestone 2.5 — Verification Engine (LLM Step 3)

**Goal:** For each requirement, determine whether the diff satisfies it — with evidence.

**Files to create:**

```
core/verification_engine.py
tests/unit/test_verification_engine.py
```

**Tasks:**
- Write the Step 3 prompt in `llm/prompts.py`
- For each requirement, send: requirement text + relevant diff hunk + repo context
- Validate response with `VerificationResult`
- Rejection rule: if `status` is `satisfied` or `partially_satisfied` and `evidence` is empty → retry once, then downgrade to `unclear`
- Requirements can be verified in parallel (use `asyncio.gather` or `ThreadPoolExecutor`)

**Done when:**
- Given `missing_tests.diff` + a requirement for tests, returns `status: "missing"` with a reason
- Given `simple_add.diff` + a requirement for an endpoint, returns `status: "satisfied"` with a file path in evidence
- Mock-based unit tests pass for both cases

---

## Milestone 2.6 — Test Adequacy Checker (LLM Step 4 supplement)

**Goal:** Identify which expected test cases are present or missing in the diff.

**Files to create:**

```
core/test_checker.py
tests/unit/test_test_checker.py
```

**Tasks:**
- Cross-reference `expected_test_cases` from Step 1 against test files in the diff
- If no test files changed at all → all expected tests are `missing`
- For each expected test case, search for related patterns in changed test hunks
- Return: list of `{test_case: str, status: "present" | "missing"}`

**Done when:**
- `missing_tests.diff` → all expected test cases flagged as missing
- A diff with a test file → at least one case detected as present

---

## Milestone 2.7 — Update Report with LLM Data

**Goal:** Replace the Phase 1 placeholder report with the full LLM-powered report.

**Files to modify:**

```
core/report_generator.py
llm/pipeline.py  (new — orchestrates all 5 steps)
```

**Tasks:**
- Create `llm/pipeline.py` — runs Steps 1–5 in order, returns all structured outputs
- Update `report_generator.py` to consume: `RequirementsOutput`, `DiffSummaryOutput`, `[VerificationResult]`, `RiskAssessmentOutput`, `FinalReportSections`, test checker results
- Generate all 11 report sections from [07_risk_scoring_and_report.md](../07_risk_scoring_and_report.md)
- Update golden snapshot in `tests/fixtures/golden_reports/`

**Done when:**
```bash
patchproof review --task task.txt
# patchproof-report.md now has:
# ✓ Executive summary (LLM-generated)
# ✓ Task completion checklist with status per requirement
# ✓ Missing tests section
# ✓ Risk score with reasons
# ✓ Suggested fixes (LLM-generated)
```

---

## Phase 2 Acceptance Criteria

```
✓ patchproof review --task task.txt produces a full 11-section report
✓ Report includes requirement checklist with satisfied/missing per item
✓ Report includes missing tests checklist
✓ Every finding has a file path and a reason (evidence rule enforced)
✓ All LLM outputs validated with Pydantic before use
✓ No real OpenAI calls made in unit tests (mocks used)
✓ Retry logic fires on malformed LLM output
```
