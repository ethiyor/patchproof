# Phase 1 — Local CLI

**Prerequisites:** None. This is the starting point.
**Reference docs:** [04_architecture.md](../04_architecture.md), [02_mvp_definition.md](../02_mvp_definition.md)

---

## Overview

Build a working Python CLI that reads a local Git diff and a task description file, applies rule-based risk scoring, and writes a Markdown report. No LLM yet — prove the data pipeline works end-to-end first.

---

## Milestone 1.1 — Project Scaffolding

**Goal:** A runnable Python project with a CLI entrypoint.

**Files to create:**

```
pyproject.toml
.env.example
.gitignore
cli/__init__.py
cli/main.py
```

**Tasks:**
- Init project with `uv init` or manual `pyproject.toml`
- Add dependencies: `typer`, `gitpython`, `pydantic`, `python-dotenv`, `httpx`
- Create `cli/main.py` with a `patchproof review` command that prints `"PatchProof ready"`
- Add `[project.scripts]` entry so `patchproof` works as a command

**Done when:**
```bash
patchproof review --help
# shows usage without errors
```

---

## Milestone 1.2 — Git Diff Collection

**Goal:** Detect the Git repo and collect the current diff.

**Files to create:**

```
cli/git_client.py
cli/config_loader.py
```

**Tasks:**
- Detect Git repo root using `git.Repo(search_parent_directories=True)`
- Collect working tree diff: `repo.git.diff()`
- Collect staged diff: `repo.git.diff("--cached")`
- Return raw unified diff text
- Handle errors: not a git repo, no changes, binary-only changes

**Done when:**
```bash
patchproof review --task task.txt
# prints: "Collected diff: 4 files changed (+187 -22)"
```

---

## Milestone 1.3 — Diff Parser

**Goal:** Convert raw unified diff text into a structured Python object.

**Files to create:**

```
core/__init__.py
core/diff_parser.py
models/__init__.py
models/diff_models.py
tests/fixtures/sample_diffs/simple_add.diff
tests/fixtures/sample_diffs/migration_change.diff
tests/unit/test_diff_parser.py
```

**Tasks:**
- Parse each changed file: path, status (added/modified/deleted/renamed), language (from extension)
- Extract hunks: context lines, additions (lines starting with `+`), deletions (lines starting with `-`)
- Count total additions and deletions per file
- Detect risky paths: check file path against list: `auth/`, `login/`, `permissions/`, `payments/`, `billing/`, `migrations/`, `.env`, `config/`, `middleware/`, `security/`, `api/routes/`
- Distinguish test files from production files (`test_`, `_test.`, `/tests/`, `/spec/`)
- Output: `ParsedDiff` Pydantic model with a list of `ParsedFile` objects

**Done when:**
- Unit tests pass for all 3 sample fixtures
- `ParsedDiff` contains correct file list, risk flags, and additions/deletions counts

---

## Milestone 1.4 — Rule-Based Risk Scorer

**Goal:** Compute a deterministic risk score from the parsed diff.

**Files to create:**

```
core/risk_scorer.py
models/risk_models.py
tests/unit/test_risk_scorer.py
```

**Tasks:**
- Implement scoring rules from [07_risk_scoring_and_report.md](../07_risk_scoring_and_report.md)
- Return: `RiskScore` Pydantic model with `score`, `level`, `reasons`
- Write unit tests for: auth path (+3), payment path (+3), migration (+2), no tests (+2), tests present (-2)

**Done when:**
- A diff touching `auth/login.py` with no test files scores at least 5 (Medium)
- A diff with tests added scores lower than the same diff without tests

---

## Milestone 1.5 — Report Generator (Basic)

**Goal:** Write a readable Markdown report from the parsed diff and risk score.

**Files to create:**

```
core/report_generator.py
tests/fixtures/golden_reports/basic_report.md
tests/unit/test_report_generator.py
```

**Tasks:**
- Generate these sections (no LLM yet):
  - Header (repo name, branch, date)
  - Risk score section with reasons
  - Risky files table (file path + risk flags)
  - Changed files summary (additions, deletions, language)
  - Placeholder note: "LLM analysis coming in Phase 2"
- Write to `patchproof-report.md` in the current directory
- Snapshot test: compare output to `golden_reports/basic_report.md`

**Done when:**
```bash
patchproof review --task task.txt
# writes patchproof-report.md with risk score and file table
```

---

## Milestone 1.6 — End-to-End Test on a Real Repo

**Goal:** Run the full Phase 1 CLI on a real diff and verify the output makes sense.

**Tasks:**
- Make a real change to one of your projects (ResearchOS, Repofy, PaperMind)
- Write a `task.txt` describing what you changed
- Run `patchproof review --task task.txt`
- Read `patchproof-report.md` and verify:
  - All changed files are listed
  - Risk flags match what you actually changed
  - Risk score feels appropriate
- Fix any bugs found
- Commit everything

**Done when:**
- The report accurately reflects what was in the diff
- No Python errors or uncaught exceptions on the real repo

---

## Phase 1 Acceptance Criteria

```
✓ patchproof review --task task.txt runs end-to-end on a real repo
✓ patchproof-report.md is written with risk score, risky files, and changed files table
✓ Unit tests pass for diff_parser, risk_scorer, and report_generator
✓ Edge cases handled: not a git repo, no changes, binary files
✓ .env.example committed, .env in .gitignore
```
