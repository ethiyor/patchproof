# What Was Built — PatchProof

This file always shows the **latest** milestone. All previous milestones are archived in [`notes/`](notes/).

| Milestone | Note |
|---|---|
| 1.1 – 1.6 | [notes/](notes/) |
| 2.1 — LLM Client | previous |
| **2.2 — LLM Output Models** | **current** |

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
