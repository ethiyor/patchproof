# What Was Built — PatchProof

This file always shows the **latest** milestone. All previous milestones are archived in [`notes/`](notes/).

| Milestone | Note |
|---|---|
| 1.1 – 1.6 | [notes/](notes/) |
| 2.1 — LLM Client | previous |
| 2.5 — Verification Engine | previous |
| 2.6 — Test Adequacy Checker | previous |
| **2.7 — Pipeline + Full Report** | **current** |

---

## Current: Phase 2 — Milestone 2.7 — Pipeline + Full Report ✅

### Phase 2 is complete.

All 5 pipeline steps are wired together. `patchproof review --task task.txt` now produces a full 11-section LLM-augmented report when `OPENAI_API_KEY` is set, and falls back to the Phase 1 basic report when it isn't.

### Files created / modified

| File | What changed |
|---|---|
| `llm/pipeline.py` | New — `run_pipeline()` orchestrates all 5 steps |
| `core/report_generator.py` | Added `generate_full_report()` + `write_full_report()` |
| `cli/main.py` | Updated — calls pipeline when API key present, falls back to Phase 1 |
| `tests/unit/test_full_report.py` | New — 22 tests |

---

### What the full report contains (11 sections)

```
1.  Header                   ← repo, branch, task, timestamp
2.  Executive Summary        ← 2–4 sentence LLM prose
3.  Merge Readiness          ← rule-based risk score + LLM recommendation
4.  Task Completion Checklist ← ✅/⚠️/❌/❓ per requirement with evidence
5.  Risk Score Details       ← bullet list of rules that fired
6.  Risky Files              ← table of files with risk flags
7.  Missing Tests            ← [ ] / [x] per expected test case
8.  Possible Bugs & Risks    ← LLM risk findings with severity + evidence
9.  Changed Files            ← table of all files
10. Suggested Fixes          ← LLM-generated action list
11. Final Recommendation     ← ✅ / ⚠️ / 🚫 with label
```

### How the pipeline is wired

```python
from llm.pipeline import run_pipeline

result = run_pipeline(
    task_text=task_text,
    diff_text=diff_result.raw,
    parsed_diff=parsed,
    risk=risk,
)
# result.requirements, .diff_summary, .verification_results,
# .risk_assessment, .test_results, .report_sections
```

The CLI checks for `OPENAI_API_KEY` at runtime:
- Set → `run_pipeline()` → `write_full_report()`
- Not set → `write_report()` (Phase 1 basic report with placeholders)

### Graceful degradation

Every pipeline step has a fallback so one failure never kills the whole run:
- Step 2 (summariser) fails → empty summary stub, pipeline continues
- Step 4 (risks) fails → empty risks list, pipeline continues
- Step 5 (sections) fails → minimal fallback with rule-based recommendation

---

## What comes next — Phase 3, Milestone 3.1

Add the GitHub REST API client so `patchproof review-pr <url>` can fetch real PR diffs from GitHub without staging anything locally.

See [docs/phases/phase_03_github_pr.md](docs/phases/phase_03_github_pr.md).

---

## Current: Phase 2 — Milestone 2.6 — Test Adequacy Checker

### What was built

`check_test_adequacy(expected_test_cases, diff)` — cross-references the expected test cases from Step 1 against the test files in the diff. No LLM — pure heuristic keyword matching. Returns one `TestCaseResult` per expected case with status `present` or `missing`.

### Files created

| File | Purpose |
|---|---|
| `core/test_checker.py` | `check_test_adequacy(cases, diff) → list[TestCaseResult]` |
| `tests/unit/test_test_checker.py` | 12 tests |

---

### Algorithm

```
1. No test files changed in diff?
   → all cases are "missing" immediately (fast path)

2. Otherwise:
   → collect all addition lines (+) from test file hunks into one searchable blob
   → for each expected test case:
       extract keywords (words ≥ 4 chars, excluding stop words)
       count keyword matches in the blob
       if matches ≥ 2 → "present"
       else           → "missing"
```

### Why keyword matching instead of the LLM?

- It's fast — no API call, no latency
- It's deterministic — same diff always produces the same result
- It's good enough for the MVP signal: "did anyone write a test touching these concepts?"
- The LLM in Step 4 (risk assessment) already flags missing tests at a higher level

The checker is intentionally conservative: 2+ keyword matches required, stop words excluded. A test for "valid PDF upload returns 200 with paper_id" needs at least 2 of `[valid, upload, returns, paper_id]` to appear in the test additions.

### Fix: `__test__ = False`

The dataclass was named `TestCaseResult`. Pytest tried to collect it as a test class because the name starts with `Test`. Adding `__test__ = False` tells pytest to skip it — the recommended way to suppress this for non-test classes whose names start with `Test`.

---

### Pipeline status

| Step | Module | Status |
|---|---|---|
| 1 — Extract requirements | `core/task_analyzer.py` | ✅ |
| 2 — Summarise diff | `core/diff_summarizer.py` | ✅ |
| 3 — Verify each requirement | `core/verification_engine.py` | ✅ |
| 4 — Test adequacy | `core/test_checker.py` | ✅ |
| 5 — Wire everything + update report | `llm/pipeline.py` | 🔜 next |

---

## What comes next — Milestone 2.7

Wire all 5 steps together in `llm/pipeline.py` and update `core/report_generator.py` to consume the LLM outputs — producing a report with a real requirement checklist, missing tests section, and suggested fixes instead of the Phase 2 placeholders.

---

## Current: Phase 2 — Milestone 2.5 — Verification Engine (LLM Step 3)

### What was built

The core of PatchProof. `verify_requirements(requirements, diff_text)` calls the LLM once per requirement and returns a `VerificationResult` for each — with status, evidence citations, and a reason. Supports parallel execution via `ThreadPoolExecutor`.

### Files created

| File | Purpose |
|---|---|
| `core/verification_engine.py` | `verify_requirements(...)` + `_verify_one(...)` |
| `tests/unit/test_verification_engine.py` | 17 tests |

---

### The downgrade safety net

The verification engine **never crashes the pipeline** over one bad requirement. When both retry attempts fail (e.g. the LLM keeps returning `satisfied` with no evidence), it downgrades the result:

```python
return VerificationResult(
    requirement=requirement,
    status="unclear",
    evidence=[],
    reason="Could not verify this requirement after 2 attempts. Last error: ...",
)
```

This means a 5-requirement task still produces a 5-row checklist even if one row fails — the user sees `unclear` with a note, not a crash.

### Parallel execution

```python
# Sequential (default — simpler, predictable order):
results = verify_requirements(reqs, diff_text)

# Parallel (faster for large requirement lists):
results = verify_requirements(reqs, diff_text, max_workers=4)
```

Uses `ThreadPoolExecutor` (not asyncio) because `call_llm` is synchronous. Order is preserved regardless of which futures complete first.

---

### Pipeline status

| Step | Module | Status |
|---|---|---|
| 1 — Extract requirements | `core/task_analyzer.py` | ✅ |
| 2 — Summarise diff | `core/diff_summarizer.py` | ✅ |
| 3 — Verify each requirement | `core/verification_engine.py` | ✅ |
| 4 — Check test adequacy | `core/test_checker.py` | 🔜 next |
| 5 — Generate report sections | `llm/pipeline.py` | 🔜 2.7 |

---

## What comes next — Milestone 2.6

Build `core/test_checker.py` — cross-reference the expected test cases from Step 1 against the test files in the diff. No LLM needed here — it's a heuristic check. If no test files changed at all, all expected tests are flagged as missing.

---

## Current: Phase 2 — Milestone 2.4 — Diff Summarizer (LLM Step 2)

### What was built

`summarize_diff(diff_text)` — sends the raw git diff to GPT-4o and returns a `DiffSummaryOutput`: a prose summary of what changed, which areas were implemented, possible side effects, and any unrelated changes spotted.

### Files created

| File | Purpose |
|---|---|
| `core/diff_summarizer.py` | `summarize_diff(diff_text: str) → DiffSummaryOutput` |
| `tests/unit/test_diff_summarizer.py` | 12 tests |

The Step 2 prompt (`STEP2_SYSTEM` + `step2_user()`) was already written in milestone 2.3.

---

### Large diff handling

Diffs can be huge. `step2_user()` truncates anything over 60,000 characters and appends `[diff truncated]` so the LLM knows context is missing:

```python
def step2_user(diff_text: str, max_chars: int = 60_000) -> str:
    truncated = diff_text[:max_chars]
    if len(diff_text) > max_chars:
        truncated += "\n\n[diff truncated — remaining files not shown]"
    return f"Unified diff:\n\n{truncated}"
```

This is the MVP approach. A more sophisticated version would summarize each file independently and merge — but truncation is correct enough for most real PRs.

---

### What the pipeline knows now

After Steps 1 + 2 complete, the pipeline holds:

```
RequirementsOutput  ← what SHOULD have been done (from task.txt)
DiffSummaryOutput   ← what WAS done (from the diff)
```

Step 3 (next) compares these two directly — for each requirement, it asks "is there evidence of this in the diff?"

---

## What comes next — Milestone 2.5

Build `core/verification_engine.py` — LLM Step 3. For each requirement from Step 1, send it alongside the relevant diff hunk and ask the model whether it's `satisfied`, `missing`, `partially_satisfied`, or `unclear`. This is the core of what makes PatchProof different from a generic PR reviewer.

---

## Current: Phase 2 — Milestone 2.3 — Task Analyzer (LLM Step 1)

### What was built

The first real prompt. `analyze_task(task_text)` sends the task description to GPT-4o and returns a validated `RequirementsOutput` — a structured list of requirements, expected test cases, and risk domains. The prompt lives in `llm/prompts.py`.

### Files created

| File | Purpose |
|---|---|
| `llm/prompts.py` | System + user prompt templates for all 5 pipeline steps |
| `core/task_analyzer.py` | `analyze_task(task_text) → RequirementsOutput` |
| `tests/unit/test_task_analyzer.py` | 13 tests — 0 real API calls |

---

## What `llm/prompts.py` contains

Five pairs of prompts — one `SYSTEM` constant and one `user()` function per step:

| Step | System prompt purpose | User template |
|---|---|---|
| `STEP1_SYSTEM` + `step1_user()` | Requirements analyst | Wraps the task text |
| `STEP2_SYSTEM` + `step2_user()` | Code change analyst | Wraps the diff text |
| `STEP3_SYSTEM` + `step3_user()` | Code reviewer | Wraps one requirement + diff hunk + context |
| `STEP4_SYSTEM` + `step4_user()` | Security reviewer | Wraps risk flags + changed files + diff summary |
| `STEP5_SYSTEM` + `step5_user()` | Technical writer | Wraps all structured results |

Every system prompt:
1. Defines the model's role
2. States the hallucination-reduction rules explicitly (*"only extract what is in the task"*)
3. Embeds the **full JSON schema** of the expected output model — generated from the Pydantic model with `model.model_json_schema()`

That third point is key: the model sees the exact field names, types, and descriptions it needs to populate. It's not guessing the format.

---

## What `analyze_task` does

```python
from core.task_analyzer import analyze_task

result = analyze_task("Add PDF upload with MIME validation and 10MB limit.")
print(result.requirements)
# ["Create POST /papers/upload endpoint",
#  "Validate MIME type — accept only application/pdf",
#  "Enforce a 10MB file size limit", ...]
```

Internally:
1. Builds `[system_message, user_message]` from `llm/prompts.py`
2. Calls `call_llm(messages)` → gets a raw dict back
3. Passes the dict to `RequirementsOutput(**raw)` → Pydantic validates every field
4. Checks that `requirements` is not empty
5. If step 3 or 4 fails, logs a warning and retries once with the same messages
6. If both attempts fail, raises `RuntimeError` with a user-facing message

---

## How prompts embed the JSON schema

```python
def _schema(model) -> str:
    return json.dumps(model.model_json_schema(), indent=2)

STEP1_SYSTEM = f"""
...
Return ONLY a JSON object matching this schema:
{_schema(RequirementsOutput)}
"""
```

`model_json_schema()` is a Pydantic v2 method that generates a JSON Schema dict from the model's field types and descriptions. The LLM sees something like:

```json
{
  "properties": {
    "requirements": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Concrete, checkable requirements extracted from the task..."
    }
  }
}
```

This is what makes the `Field(description=...)` annotations from milestone 2.2 useful — they flow directly into the prompt.

---

## What comes next — Milestone 2.4

Build `core/diff_summarizer.py` — LLM Step 2. It takes the parsed diff and returns a `DiffSummaryOutput` describing what changed in plain language. After 2.4, the pipeline will know both what *should* have been done (Step 1) and what *was* done (Step 2).

---

## Current: Phase 2 — Milestone 2.2 — Pydantic Output Models

### What was built

Strict Pydantic models for every shape that comes back from the LLM. Every pipeline step validates its output against one of these models before moving on. If the LLM returns a wrong type, a missing field, or violates the evidence rule, a `ValidationError` is raised immediately.

### Files created

| File | What's in it |
|---|---|
| `models/llm_outputs.py` | 7 models for all 5 pipeline steps |
| `tests/unit/test_llm_models.py` | 28 tests |

---

## The 7 Models

| Model | Step | Key constraint |
|---|---|---|
| `RequirementsOutput` | 1 | `requirements` must be a list of strings |
| `DiffSummaryOutput` | 2 | `change_summary` required |
| `VerificationResult` | 3 | `satisfied`/`partially_satisfied` require non-empty `evidence` |
| `RiskFinding` | 4 | `category` and `severity` are `Literal` enums |
| `RiskAssessmentOutput` | 4 | Wraps a list of `RiskFinding` |
| `FinalReportSections` | 5 | `merge_recommendation` is a `Literal` enum |

---

## The Evidence Rule (most important constraint)

`VerificationResult` has a `@model_validator` that enforces the core PatchProof principle:

```python
@model_validator(mode="after")
def _evidence_required_when_satisfied(self) -> "VerificationResult":
    if self.status in ("satisfied", "partially_satisfied") and not self.evidence:
        raise ValueError(
            "status='satisfied' requires at least one evidence citation."
        )
    return self
```

**Why:** The LLM can claim a requirement is satisfied even when it isn't. Requiring a file:line citation forces the model to point to something concrete in the diff. If it can't find evidence, it must use `unclear` or `missing` instead. This is what separates PatchProof from vague AI PR comments.

---

## `Field(description=...)` — Why It Matters

Every field has a `description` annotation:

```python
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
```

These descriptions are not just for human readers. When we generate a JSON schema from the model (which we send to the LLM as part of the prompt), the descriptions tell the model exactly what format and content each field expects. Better descriptions → fewer malformed responses → fewer retries.

---

## What comes next — Milestone 2.3

Write `llm/prompts.py` (the actual text sent to GPT-4o for Step 1) and `core/task_analyzer.py` (which calls it and validates the response). After 2.3, running the CLI will extract a real structured requirement list from `task.txt` using the LLM.

---

## Current: Phase 2 — Milestone 2.1 — LLM Client Setup

### What was built

A reusable, testable OpenAI wrapper in `llm/client.py`. It handles JSON mode, temperature, retry logic, token usage logging, and API key security. All 5 pipeline steps will call `call_llm()` — this is the foundation they all share.

### Files created

| File | Purpose |
|---|---|
| `llm/client.py` | `call_llm(messages) → dict` — OpenAI wrapper |
| `tests/mocks/llm_responses.py` | Fixture dicts for all 5 LLM pipeline steps |
| `tests/unit/test_llm_client.py` | 15 tests — 0 real API calls |

---

## How `call_llm` works

```python
from llm.client import call_llm

result = call_llm([
    {"role": "system", "content": "Extract requirements as JSON."},
    {"role": "user", "content": "Add PDF upload support with MIME validation."},
])
# result is a parsed Python dict
```

Every call uses:
- `response_format={"type": "json_object"}` — forces the model to always return valid JSON
- `temperature=0.1` — near-deterministic output
- `model="gpt-4o"` — configurable per call

### Retry logic

Three retryable error types:

| Error | Delay | Why retryable |
|---|---|---|
| `APIConnectionError` | 2s | Transient network blip |
| `RateLimitError` | 5s | Temporary quota exceeded |
| `json.JSONDecodeError` | 2s | Model returned malformed JSON (rare) |

`AuthenticationError` and other `APIError` subclasses are **not retried** — they indicate a programming error (wrong key, bad request), not a transient failure.

### Security rule

The full `OPENAI_API_KEY` is never logged. Only the first 4 characters appear in debug output: `sk-****`. This is tested explicitly in `TestApiKeySecurity`.

### How mocking works in tests

```python
from unittest.mock import patch

with patch("llm.client.OpenAI") as mock_openai:
    mock_openai.return_value.chat.completions.create.return_value = mock_response
    result = call_llm([...])
    # call_llm ran — no real HTTP request made
```

`patch("llm.client.OpenAI")` replaces the `OpenAI` class inside `llm/client.py` with a `MagicMock`. When `_make_client()` calls `OpenAI(api_key=...)`, it gets the mock instead. All chained attribute accesses (`client.chat.completions.create(...)`) return whatever you set up. The real OpenAI SDK is never invoked.

---

## What comes next — Milestone 2.2

Define Pydantic models for all 5 LLM response shapes in `models/llm_outputs.py`. These will validate every response from `call_llm` before it enters the pipeline — if the LLM returns an unexpected shape, the error is caught immediately with a clear message.

---

## Current: Phase 1 — Milestone 1.6 — End-to-End Test ✅

### Phase 1 is complete.

The full pipeline works on a real repo:

```
git diff  →  parse_diff()  →  compute_risk()  →  write_report()  →  patchproof-report.md
```

### Bug found and fixed: untracked files were invisible

`git diff HEAD` only sees files git already knows about. New files that haven't been committed yet were silently missing from the diff — and therefore from the report.

**Fix:** After getting the tracked diff, loop through `repo.untracked_files` and generate a synthetic diff for each new file using `git diff --no-index /dev/null <file>`. Uses `subprocess.run()` directly because GitPython raises `GitCommandError` for this command even on success (exit code 1 = files differ, which is the normal case).

### Final verified output

```
patchproof review --task task.txt
Repo    : patchproof  [main]
Diff    : 4 files changed (+136 -4)
Risk    : 2 (Low)
Report  : patchproof-report.md  ✓

Changed Files:
  cli/git_client.py          modified  python    +30  -3
  docs/phases/...            modified  markdown   +1  -0
  task.txt                   modified  —          +1  -1
  README.md                  added     markdown  +104  -0
```

### Phase 1 acceptance criteria — all met

```
✓ patchproof review --task task.txt runs end-to-end on a real repo
✓ patchproof-report.md written: risk score, risky files, changed files table
✓ 97 unit tests pass (diff_parser, risk_scorer, report_generator)
✓ Edge cases handled: not a git repo, no changes, untracked files
✓ .env.example committed, .env in .gitignore
✓ Committed and pushed to GitHub
```

---

## What comes next — Phase 2, Milestone 2.1

Add the LLM brain. Start with `llm/client.py` — an OpenAI wrapper with retry and error handling. This is the foundation all 5 LLM pipeline steps will use.

See [docs/phases/phase_02_llm_pipeline.md](docs/phases/phase_02_llm_pipeline.md) for the full plan.

---

## Current: Phase 1 — Milestone 1.5 — Report Generator (Basic)

### What was built

A Markdown report generator that takes a `ParsedDiff` and `RiskScore` and writes a structured `patchproof-report.md` to disk. This completes the Phase 1 data pipeline:

```
git diff  →  parse_diff()  →  compute_risk()  →  write_report()  →  patchproof-report.md
```

### Files created / modified

| File | What changed |
|---|---|
| `core/report_generator.py` | New — `generate_report()` + `write_report()` |
| `tests/fixtures/golden_reports/basic_report.md` | New — committed snapshot of expected output |
| `tests/unit/test_report_generator.py` | New — 31 tests across 5 classes |
| `cli/main.py` | Updated — full pipeline wired end-to-end |

---

## How the Report Generator Works

The generator takes structured inputs and builds a Markdown string line by line:

```python
lines: list[str] = []
lines += ["# PatchProof Report", ""]
lines += [f"**Repository:** {repo_name}  ", f"**Branch:** {branch}  "]
# ... sections ...
return "\n".join(lines) + "\n"
```

### Report sections (Phase 1)

```
# PatchProof Report           ← header: repo, branch, task, timestamp
## Merge Readiness            ← risk score + level with emoji (🟢🟡🔴🚨)
## Risk Score Details         ← bullet list of every rule that fired
## Risky Files                ← table of files with risk flags
## Changed Files              ← table of all files with +additions/-deletions
## Task Completion Checklist  ← Phase 2 placeholder
## Missing Tests              ← Phase 2 placeholder
## Final Recommendation       ← Phase 2 placeholder
```

---

## Key Design: Injecting Time for Testability

```python
def generate_report(..., generated_at: str | None = None) -> str:
    ts = generated_at or _now_utc()   # production: real time; tests: fixed string
```

A function that calls `datetime.now()` internally cannot be tested with exact string comparison — the timestamp changes every run. Accepting time as a parameter makes the function **pure**: same input → same output every time.

---

## Key Design: Golden Snapshot Test

```python
def test_matches_golden_file():
    result = generate_report(..., generated_at="2026-07-05 00:00 UTC")
    expected = Path("tests/fixtures/golden_reports/basic_report.md").read_text()
    assert result == expected
```

If the report format ever changes unintentionally, this test fails immediately. To update: delete the golden file and re-run — the test recreates it, then verifies on every subsequent run.

---

## Full pipeline output

```bash
patchproof review --task task.txt
Repo    : patchproof  [master]
Diff    : 28 files changed (+4288 -0)
Risk    : 8 (High)
Report  : patchproof-report.md  ✓
```

---

## Verify it yourself

```bash
source .venv/bin/activate
pytest tests/unit/ -q          # 97 passed
patchproof review --task task.txt
cat patchproof-report.md
```

---

## What comes next — Milestone 1.6

Run the CLI on a real diff from one of your other projects (ResearchOS, Repofy, PaperMind). Verify the report is accurate, fix any edge cases, and make the first real commit.
# test change

