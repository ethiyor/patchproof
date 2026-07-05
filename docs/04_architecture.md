# 04 — Architecture, Tech Stack & Core Modules

## High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Entry Points                             │
│                                                                 │
│  ┌─────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Local CLI  │  │  GitHub PR CLI   │  │  GitHub Webhook  │  │
│  └──────┬──────┘  └────────┬─────────┘  └────────┬─────────┘  │
└─────────┼──────────────────┼─────────────────────┼────────────┘
          │                  │                      │
          └──────────────────┼──────────────────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │      FastAPI Backend      │
              │  POST /reviews/local      │
              │  POST /reviews/github-pr  │
              │  POST /github/webhook     │
              └──────────────┬───────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  Diff Parser   │  │ Task Analyzer  │  │  Repo Context  │
│                │  │                │  │  Retriever     │
│ files, hunks,  │  │ requirements,  │  │ related tests, │
│ risky paths,   │  │ expected tests,│  │ models, routes,│
│ lang detection │  │ risk domains   │  │ API clients    │
└───────┬────────┘  └───────┬────────┘  └───────┬────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
              ┌──────────────────────────┐
              │      LLM Pipeline         │
              │  Step 1: Extract reqs     │
              │  Step 2: Summarize diff   │
              │  Step 3: Verify each req  │
              │  Step 4: Check risks      │
              │  Step 5: Generate report  │
              └──────────────┬───────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ Verification   │  │  Risk Scoring  │  │ Test Adequacy  │
│ Engine         │  │  Engine        │  │ Checker        │
│                │  │                │  │                │
│ req status +   │  │ rule-based +   │  │ test files     │
│ evidence       │  │ LLM score      │  │ coverage gaps  │
└───────┬────────┘  └───────┬────────┘  └───────┬────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
              ┌──────────────────────────┐
              │    API Contract Checker   │
              │  backend response fields  │
              │  vs frontend expectations │
              └──────────────┬───────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │     Report Generator      │
              └────┬─────────────────┬───┘
                   │                 │
         ┌─────────▼──────┐  ┌──────▼────────────┐
         │ patchproof-    │  │ PostgreSQL (Ph 4+) │
         │ report.md      │  └───────────────────┘
         └────────────────┘
                   │
                   ▼ (Phase 5+)
         ┌──────────────────────┐
         │  GitHub PR Comment   │
         └──────────────────────┘
```

---

## Data Flow: Task + Diff → Final Report

```
INPUTS
  task.txt / PR body / linked issue
  git diff / GitHub PR diff
  optional: test output, CI result
         │
         ▼
PARSE
  diff  → ParsedDiff: file list, hunks, risk flags per file
  task  → structured requirements, expected test areas
         │
         ▼
RETRIEVE CONTEXT (heuristic in MVP, AST/embeddings later)
  for each changed file → find related models, tests, services, API clients
         │
         ▼
LLM PIPELINE — 5 focused prompts, Pydantic-validated outputs
  1. Extract requirements from task
  2. Summarize diff
  3. Verify each requirement against diff + context
  4. Assess risks
  5. Check test adequacy
         │
         ▼
SCORING + CHECKING
  Hybrid risk score (rule-based points + LLM ±2 adjustment)
  Test adequacy check (expected vs found test cases)
  API contract check (backend response fields vs frontend reads)
         │
         ▼
REPORT ASSEMBLY
  All structured outputs → Markdown report sections
  Merge recommendation determined from risk level + requirement statuses
         │
         ▼
OUTPUT
  patchproof-report.md (all phases)
  PostgreSQL row       (Phase 4+)
  GitHub PR comment    (Phase 5+)
  Dashboard view       (Phase 6+)
```

---

## Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| CLI | Python 3.12+, Typer | Fast to build, easy to distribute |
| Backend | FastAPI, Uvicorn | Async, type-safe, fast to develop |
| Database | PostgreSQL | Reliable, good JSONB support |
| ORM | SQLAlchemy 2.0 async + Alembic | Industry standard, migration support |
| Queue | FastAPI BackgroundTasks → Redis + RQ later | Start simple |
| Frontend | React + Vite + Tailwind CSS | Fast setup, component-driven |
| Git integration | GitPython | Pure Python diff extraction |
| GitHub API | httpx + raw REST | Direct control, no magic |
| LLM | OpenAI API (GPT-4o), model-agnostic design | Best structured output today |
| Validation | Pydantic v2 | Validate every LLM response before use |
| Static analysis | ruff, eslint, mypy | Augment LLM with deterministic checks |
| Testing | pytest, pytest-asyncio, respx | Async-safe, mocking-friendly |
| Config | pydantic-settings, .env | Secret separation |
| Deployment | Docker Compose → Render or Fly.io | Cheap, fast |
| Future Rust | Diff parser or CLI binary | Only if performance is a bottleneck |

---

## Core Modules

### `cli/main.py` — CLI Layer
Entry point for all user-facing commands.
- Register Typer commands: `review`, `review-pr`
- Accept flags: `--task`, `--diff`, `--staged`, `--output`
- Load config from env or `~/.patchproof/config.toml`
- Call git client, diff collector, analysis engine
- Print status to terminal, write report to disk

### `cli/git_client.py` — Git Diff Collector
Extract a diff from the local Git repository.
- Detect Git repo root using GitPython
- Collect diff from working tree, staged changes, or branch/commit range
- Return raw unified diff text
- Handle edge cases: not a git repo, no changes, binary files

### `cli/github_client.py` — GitHub PR Fetcher
Fetch PR data from GitHub REST API.
- Parse GitHub PR URL into owner, repo, PR number
- Authenticate with `GITHUB_TOKEN` from environment
- Fetch PR metadata and diff (`application/vnd.github.diff`)
- Fetch linked issue body if present
- Handle rate limits, missing tokens, 404 errors

### `core/diff_parser.py` — Diff Parser
Convert raw unified diff text into structured data.
- Parse each file: path, status (added/modified/deleted/renamed), language
- Extract hunks, count additions/deletions
- Detect risky paths: `auth/`, `login/`, `payments/`, `migrations/`, `.env`, etc.
- Output: `ParsedDiff` Pydantic model

### `core/task_analyzer.py` — Task / Spec Analyzer
Convert task description into structured requirements (LLM Step 1).
- Send task text to LLM
- Extract: requirements list, expected test areas, risk domains
- Validate output with Pydantic
- Fall back gracefully if LLM output is malformed

### `core/repo_context.py` — Repo Context Retriever
Find files related to the changed files (MVP: heuristics only).
- If `backend/routes/X.py` changed → retrieve model, service, tests for X
- If frontend component changed → retrieve API client, page, types
- If migration added → retrieve related model
- Future: AST parsing, import graphs, embeddings

### `core/verification_engine.py` — Requirement Verification Engine
The heart of PatchProof. Verify each requirement against the diff (LLM Step 3).
- For each requirement, produce status + evidence + reason
- Statuses: `satisfied`, `partially_satisfied`, `missing`, `unclear`, `out_of_scope_change`
- Reject findings without evidence, retry once
- Prefer fewer high-confidence findings

### `core/risk_scorer.py` — Risk Scoring Engine
Compute a hybrid risk score from rules + LLM judgment.
- Rule-based scoring from risky path flags and diff statistics
- LLM qualitative adjustment (±2 cap)
- Output: score (int), level (`low/medium/high/critical`), reasons list

### `core/test_checker.py` — Test Adequacy Checker
Determine whether the PR added meaningful tests.
- Detect changed test files
- Cross-reference with changed production files
- Identify expected test cases for the task
- Report which expected cases are present vs missing

### `core/api_contract_checker.py` — API Contract Checker
Detect frontend/backend contract mismatches.
- Find changed backend route files
- Extract response field names from changed return statements
- Find frontend files that call those routes
- Compare field names heuristically, flag mismatches

### `core/report_generator.py` — Report Generator
Assemble all outputs into a readable Markdown report.
- Consume: requirement checks, risk score, test findings, API findings, diff summary
- Render each section with consistent formatting
- Apply merge recommendation logic
- Write `patchproof-report.md` (Phase 4+: also save to database)

### `db/models.py` + `db/session.py` — Database / Storage Layer
Persist reviews and findings (Phase 4+).
- SQLAlchemy async ORM models
- Alembic migrations
- Async session factory

### `frontend/` — Dashboard (Phase 6+)
React web UI for review history and analytics.
- Reviews list with risk badges
- Review detail with full report sections
- Risk trend chart, finding filters
