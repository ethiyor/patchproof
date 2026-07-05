# What Was Built — PatchProof

This file always shows the **latest** milestone. All previous milestones are archived in [`notes/`](notes/).

| Milestone | Note |
|---|---|
| 1.1 — Scaffolding | [notes/1.1_scaffolding.md](notes/1.1_scaffolding.md) |
| 1.2 — Git Diff Collection | [notes/1.2_git_diff.md](notes/1.2_git_diff.md) |
| 1.3 — Diff Parser | [notes/1.3_diff_parser.md](notes/1.3_diff_parser.md) |
| 1.4 — Risk Scorer | [notes/1.4_risk_scorer.md](notes/1.4_risk_scorer.md) |
| 1.5 — Report Generator | [notes/1.5_report_generator.md](notes/1.5_report_generator.md) |
| **1.6 — End-to-End Test** | **current** |

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
