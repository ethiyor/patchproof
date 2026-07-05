# 09 — Resume Milestones & Next Steps

## Resume-Ready Milestones

| Version | Resume bullet |
|---|---|
| **v0.1 — Local CLI** | Built PatchProof CLI in Python that parses Git diffs, applies rule-based risk scoring across auth/db/config/payment paths, and writes structured merge-readiness reports to Markdown. |
| **v0.2 — LLM Pipeline** | Extended PatchProof with a 5-step modular LLM pipeline (OpenAI GPT-4o) that extracts requirements from task descriptions, verifies each requirement against the diff with evidence citations, and detects missing tests. |
| **v0.3 — GitHub PR** | Added GitHub REST API integration; PatchProof can now fetch and analyze any GitHub pull request from a URL using the unified diff endpoint. |
| **v0.4 — Backend + DB** | Built a FastAPI backend with PostgreSQL persistence (SQLAlchemy async + Alembic migrations); all reviews and findings are stored and queryable by ID. |
| **v0.5 — GitHub App** | Deployed PatchProof as a GitHub App that automatically posts merge-readiness reports as PR comments when a pull request is opened or updated, with HMAC-SHA256 webhook verification and JWT-based installation auth. |
| **v0.6 — Dashboard** | Built a React + Tailwind dashboard showing review history, per-PR risk scores, finding categories, and risk trend charts. |
| **v0.7 — VS Code Extension** | Built a VS Code extension with a sidebar panel that runs PatchProof on uncommitted local changes and displays the report inline without leaving the editor. |
| **Final** | Built PatchProof — a spec-to-merge verification tool for AI-generated code changes. Analyzes GitHub PRs against task specifications, verifies requirement completion with evidence, scores risk across auth/database/API/security domains, detects missing tests, checks API contracts, and generates evidence-based merge-readiness reports via CLI, GitHub App, and web dashboard. |

---

## Next 7 Days — Concrete Checklist

### Day 1 — Project Scaffolding

```
[ ] Create patchproof/ folder and init git repo
[ ] Set up pyproject.toml with uv (Python 3.12)
[ ] Install dependencies: typer, gitpython, pydantic, python-dotenv, httpx
[ ] Create .env.example with OPENAI_API_KEY and GITHUB_TOKEN placeholders
[ ] Create cli/main.py with a basic `patchproof review` command that prints "hello"
[ ] Verify: python -m patchproof review runs without errors
```

### Day 2 — Git Diff Collection

```
[ ] Implement cli/git_client.py — detect repo root, collect diff from working tree
[ ] Test it: run on ResearchOS or Repofy and print raw diff to terminal
[ ] Handle edge cases: not a git repo, no changes, binary files
[ ] Verify: patchproof review --task task.txt prints the raw diff
```

### Day 3 — Diff Parser

```
[ ] Implement core/diff_parser.py — parse unified diff into ParsedDiff Pydantic model
[ ] Extract: file paths, status, language, additions, deletions, hunks, risky path flags
[ ] Write unit tests with 3 sample diff fixtures (simple add, rename, migration)
[ ] Verify: parser returns correct structured data for each fixture
```

### Day 4 — Rule-Based Risk Scorer + Basic Report

```
[ ] Implement core/risk_scorer.py — apply the scoring table from docs/07_risk_scoring_and_report.md
[ ] Implement core/report_generator.py — write patchproof-report.md with risk score + file list
[ ] Verify: patchproof review --task task.txt writes a real (if basic) Markdown report
```

### Day 5 — LLM Client + Task Analyzer

```
[ ] Implement llm/client.py — wrap OpenAI call with retry and error handling
[ ] Implement core/task_analyzer.py — LLM Step 1 (requirement extraction)
[ ] Create models/llm_outputs.py — Pydantic models for RequirementsOutput
[ ] Test: run with a real task.txt and print extracted requirements to terminal
```

### Day 6 — Verification Engine

```
[ ] Implement core/verification_engine.py — LLM Step 3 (per-requirement check)
[ ] Add Pydantic models for VerificationResult
[ ] Add retry logic for missing evidence
[ ] Update report to include task completion checklist with status + evidence
[ ] Verify: report now shows a checklist section
```

### Day 7 — End-to-End Test on a Real Project

```
[ ] Run patchproof review --task task.txt on a real recent diff from one of your projects
[ ] Read the report and verify accuracy against what the diff actually does
[ ] Fix any bugs or prompt issues found
[ ] Commit everything with a clean initial commit
[ ] Write a short README.md with install steps and one usage example
```
