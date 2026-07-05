# PatchProof — Product Spec and Architecture

## 1. Product Definition

**PatchProof** is a developer tool that verifies AI-generated code changes before they are merged.

The product analyzes a Git diff or GitHub pull request against the original task description and produces a structured **merge-readiness report**.

PatchProof is not mainly an AI code reviewer. It is a **verification layer** for AI-written or AI-assisted software changes.

## 2. Core Problem

AI coding tools can produce code quickly, but developers still need to answer:

* Did the AI actually complete the requested task?
* Did it change unrelated files?
* Did it introduce risky changes in authentication, database, APIs, config, security, or payments?
* Did it add or update meaningful tests?
* Did the frontend/backend contract remain consistent?
* What exactly should the human reviewer inspect before merging?

Existing tools already do AI PR review, PR summaries, inline comments, and context-aware suggestions. PatchProof should focus on **task alignment, risk, tests, and merge evidence**, because that is a clearer wedge.

## 3. Target Users

### Primary user

Small engineering teams using Cursor, Copilot Agent, Codex, Claude Code, Devin, or other AI coding agents.

### Secondary user

Individual developers who use AI heavily and want to review their local changes before committing.

### First user for MVP

You.

Use PatchProof on your own projects: ResearchOS, FurnishUp parser work, Repofy, PaperMind, FastAPI practice projects, and any GitHub PRs you make.

## 4. Main Workflow

### MVP workflow

```text
User gives PatchProof:
1. Git diff or GitHub PR link
2. Original task description
3. Optional test output

PatchProof returns:
1. Change summary
2. Task completion checklist
3. Risk score
4. Missing tests
5. Risky files touched
6. Possible bugs or mismatches
7. Human reviewer checklist
8. Final merge recommendation
```

### Example

```text
Task:
Add PDF upload support.

PatchProof Report:
Merge readiness: Not ready
Risk level: Medium-high

Completed:
✓ Added /papers/upload endpoint
✓ Added frontend upload form
✓ Stores paper metadata

Missing:
✗ No file size limit
✗ No MIME validation
✗ No test for invalid PDF
✗ No frontend error state

Human reviewer should inspect:
1. backend/routes/upload.py
2. backend/services/storage.py
3. frontend/components/PaperUpload.tsx
4. migrations/003_create_papers.sql
```

## 5. Product Differentiation

PatchProof should not compete directly on generic line-by-line review.

Its core differentiation:

```text
Spec → Diff → Tests → Risk → Evidence → Merge Decision
```

### Existing AI code review tools often ask:

```text
What issues are in this PR?
```

### PatchProof asks:

```text
Can we prove this PR is ready to merge for the task it claims to solve?
```

## 6. MVP Scope

The first version should be a **local CLI**, not a full GitHub App.

### Version 1: Local CLI

Command:

```bash
patchproof review --task task.txt
```

or:

```bash
patchproof review --diff changes.diff --task task.txt
```

Output:

```bash
patchproof-report.md
```

The CLI should analyze the current Git working tree or a saved diff.

### Version 2: GitHub PR Analyzer

Command:

```bash
patchproof review-pr https://github.com/org/repo/pull/12 --task task.txt
```

The app fetches the PR diff and metadata from GitHub.

### Version 3: GitHub App

PatchProof automatically runs when a PR is opened or updated and posts a merge-readiness report as a PR comment.

### Version 4: Dashboard

A web dashboard shows PR history, risk scores, common AI mistakes, and team-level patterns.

### Version 5: VS Code / Cursor Extension

A developer can review uncommitted local changes before committing.

## 7. High-Level Architecture

```text
                ┌──────────────────────┐
                │   CLI / GitHub App    │
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │   FastAPI Backend     │
                └──────────┬───────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐   ┌────────────────┐   ┌────────────────┐
│ Diff Parser  │   │ Repo Analyzer  │   │ Task Analyzer  │
└──────┬───────┘   └───────┬────────┘   └───────┬────────┘
       │                   │                    │
       └───────────────────┼────────────────────┘
                           ▼
                ┌──────────────────────┐
                │ Verification Engine   │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ Risk Scoring Engine   │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ Report Generator      │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ Markdown / PR Comment │
                └──────────────────────┘
```

## 8. Technical Stack

### Best stack for you

```text
CLI:
Python first, Rust later if you want performance

Backend:
FastAPI

Database:
PostgreSQL

Queue:
Redis + RQ or Celery

Frontend dashboard:
React + Tailwind

Git integration:
GitPython for local repos
GitHub REST API for PRs

LLM:
OpenAI API or another model API

Static analysis:
ruff / eslint / mypy / pytest / npm test depending on repo type

Deployment:
Render, Railway, Fly.io, or Docker on a VPS
```

Start with Python because it is faster for the MVP. Later, if you want a stronger systems angle, rewrite the diff parser or CLI in Rust.

## 9. Main Components

## 9.1 CLI Layer

The CLI is the first product.

Responsibilities:

* Detect current Git repository
* Collect changed files
* Generate diff
* Read task description
* Optionally run tests
* Send payload to local engine or backend
* Save Markdown report

Example commands:

```bash
patchproof review --task task.txt
patchproof review --staged --task task.txt
patchproof review --diff pr.diff --task task.txt
patchproof review-pr <github-pr-url> --task task.txt
```

Implementation modules:

```text
cli/
  main.py
  git_client.py
  diff_collector.py
  test_runner.py
  config_loader.py
```

## 9.2 GitHub Integration

For GitHub PRs, PatchProof needs to:

* Fetch PR metadata
* Fetch changed files
* Fetch diff/patch
* Read linked issue if available
* Post a PR comment in later versions
* Receive webhook events in GitHub App version

GitHub’s REST API supports pull request operations and diff/patch media types, and webhooks can send PR event payloads to your server.

GitHub App permissions matter because the app should request the minimum needed access. GitHub’s documentation says App permissions define what resources the app can access through the API.

Recommended initial GitHub App permissions:

```text
Contents: read
Pull requests: read/write
Issues: read
Checks: read
Metadata: read
```

Only request write permission when you need to post PR comments.

## 9.3 Diff Parser

Input:

```text
git diff
```

Output:

```json
{
  "files": [
    {
      "path": "backend/routes/upload.py",
      "status": "modified",
      "language": "python",
      "additions": 43,
      "deletions": 8,
      "hunks": [...]
    }
  ]
}
```

Responsibilities:

* Parse changed files
* Identify file types
* Extract hunks
* Count additions/deletions
* Detect renamed/deleted files
* Detect risky paths

Risky path examples:

```text
auth/
login/
permissions/
payments/
billing/
migrations/
.env
config/
middleware/
security/
api/
routes/
```

## 9.4 Task Analyzer

Input:

```text
Task description or issue body
```

Output:

```json
{
  "goal": "Add PDF upload support",
  "requirements": [
    "Create upload endpoint",
    "Store paper metadata",
    "Add frontend upload form",
    "Validate file type",
    "Handle upload errors"
  ],
  "expected_files": [
    "backend routes",
    "storage service",
    "frontend upload component",
    "database model"
  ],
  "risk_domains": ["file_upload", "storage", "database"]
}
```

Responsibilities:

* Convert task into concrete requirements
* Identify expected implementation areas
* Identify expected tests
* Identify security-sensitive requirements

## 9.5 Repo Context Retriever

This is what makes PatchProof smarter than a simple diff checker.

Responsibilities:

* Retrieve files related to the changed files
* Find tests related to changed modules
* Find API route definitions
* Find database models
* Find frontend API clients
* Find config and schema files

For MVP, use simple heuristics:

```text
If backend/routes/papers.py changed:
- retrieve backend/models/paper.py
- retrieve backend/services/paper_service.py
- retrieve tests/test_papers.py

If frontend upload component changed:
- retrieve API client
- retrieve page using that component
- retrieve types/interfaces
```

Later, add AST parsing and embeddings.

## 9.6 Verification Engine

This is the heart of PatchProof.

The verification engine compares:

```text
Task requirements
        vs
Code diff
        vs
Repo context
        vs
Tests
```

It produces:

```json
{
  "requirements": [
    {
      "requirement": "Validate uploaded file type",
      "status": "missing",
      "evidence": [],
      "reason": "The upload endpoint accepts the file without checking MIME type or extension."
    }
  ]
}
```

Requirement statuses:

```text
satisfied
partially_satisfied
missing
unclear
out_of_scope_change
```

## 9.7 Risk Scoring Engine

Risk score should not be pure LLM vibes. Use a hybrid system:

```text
Rule-based score + LLM judgment + test evidence
```

Example risk factors:

```text
+3 touches auth/security
+3 touches payment/billing
+2 touches database migration
+2 no tests changed
+2 user input/file upload
+2 public API contract changed
+1 config/env changed
+1 large PR
+1 many files touched
-2 tests added
-1 docs updated
-2 CI passed
```

Risk levels:

```text
0–2: Low
3–5: Medium
6–8: High
9+: Critical
```

Example:

```json
{
  "risk_score": 7,
  "risk_level": "high",
  "reasons": [
    "User-uploaded files introduced",
    "No validation tests added",
    "Database model changed",
    "No file size limit found"
  ]
}
```

## 9.8 Test Adequacy Checker

This component checks whether the PR adds or updates meaningful tests.

It should answer:

* Did any test files change?
* Are tests related to the changed feature?
* Do tests cover success cases?
* Do tests cover failure cases?
* Are security/risk cases tested?
* Did CI pass?

For MVP, do not try to prove test quality deeply. Start with practical checks:

```text
If feature touches file upload:
Expected tests:
- valid file upload
- invalid file type
- oversized file
- empty file
- backend error handling
```

## 9.9 API Contract Checker

This is a strong differentiator.

It checks whether frontend and backend still agree.

Example:

Backend returns:

```json
{
  "paper_id": "abc123"
}
```

Frontend expects:

```ts
response.data.id
```

PatchProof should flag:

```text
Possible API contract mismatch:
Backend returns paper_id, but frontend reads id.
```

MVP approach:

* Look for changed backend route response fields
* Look for frontend API calls to that route
* Compare JSON keys heuristically
* Later add OpenAPI schema generation

## 9.10 Report Generator

The final report should be structured and readable.

Report sections:

```text
1. Executive summary
2. Merge readiness
3. Task completion checklist
4. Risk score
5. Risky files touched
6. Missing tests
7. Possible bugs
8. API/database/security concerns
9. Human reviewer checklist
10. Suggested fixes
```

Final recommendation:

```text
Ready to merge
Ready with minor comments
Needs changes
Do not merge
```

## 10. Backend API Design

### POST /reviews/local

Used by CLI.

Request:

```json
{
  "repo_name": "papermind",
  "task": "...",
  "diff": "...",
  "changed_files": [...],
  "test_output": "..."
}
```

Response:

```json
{
  "review_id": "rev_123",
  "status": "completed",
  "report_markdown": "...",
  "risk_score": 7,
  "merge_recommendation": "needs_changes"
}
```

### POST /reviews/github-pr

Used for PR URL review.

Request:

```json
{
  "pr_url": "https://github.com/user/repo/pull/12",
  "task": "Add PDF upload support"
}
```

### GET /reviews/{review_id}

Returns a saved review.

### POST /github/webhook

Receives GitHub PR webhook events in GitHub App version.

### POST /reviews/{review_id}/comment

Posts the report back to the PR.

## 11. Database Schema

### users

```sql
id
email
created_at
```

### repositories

```sql
id
owner
name
provider
installation_id
created_at
```

### pull_requests

```sql
id
repository_id
pr_number
title
author
base_branch
head_branch
status
created_at
updated_at
```

### reviews

```sql
id
repository_id
pull_request_id
task_text
risk_score
risk_level
merge_recommendation
report_markdown
created_at
```

### review_findings

```sql
id
review_id
category
severity
title
description
file_path
line_start
line_end
evidence
suggestion
created_at
```

Categories:

```text
task_alignment
missing_test
security
database
api_contract
config
dependency
bug_risk
out_of_scope
```

### requirement_checks

```sql
id
review_id
requirement_text
status
evidence
reason
created_at
```

### changed_files

```sql
id
review_id
file_path
status
language
additions
deletions
risk_flags
```

## 12. LLM Pipeline

Use the LLM in separate steps. Do not ask one giant prompt to do everything.

### Step 1: Extract requirements

Input:

```text
Task description
```

Output:

```json
{
  "requirements": [...],
  "expected_tests": [...],
  "risk_domains": [...]
}
```

### Step 2: Summarize diff

Input:

```text
Changed files + hunks
```

Output:

```json
{
  "change_summary": "...",
  "implemented_areas": [...],
  "possible_side_effects": [...]
}
```

### Step 3: Verify each requirement

Input:

```text
Requirement + relevant diff/context
```

Output:

```json
{
  "status": "satisfied | partially_satisfied | missing | unclear",
  "evidence": [...],
  "reason": "..."
}
```

### Step 4: Check risks

Input:

```text
Risk flags + diff + repo context
```

Output:

```json
{
  "risks": [...]
}
```

### Step 5: Generate final report

Input:

```text
Structured requirement checks + risk checks + test checks
```

Output:

```markdown
PatchProof Report...
```

This modular design makes the system easier to debug and less likely to hallucinate.

## 13. Important Product Rule

Every finding should include evidence.

Bad:

```text
This code may be insecure.
```

Good:

```text
File upload endpoint accepts user files, but no MIME type check or file-size limit appears in backend/routes/upload.py.
```

PatchProof should prefer fewer, higher-confidence findings over many noisy comments.

## 14. What to Build First

### Week 1: CLI + Local Diff Report

Build:

```text
- Python CLI
- Read git diff
- Read task.txt
- Parse changed files
- Generate Markdown report
- Basic risk rules
```

No database. No frontend. No GitHub App yet.

### Week 2: LLM Requirement Verification

Add:

```text
- Task analyzer
- Diff summarizer
- Requirement checklist
- Missing tests section
- Better report format
```

### Week 3: GitHub PR Fetching

Add:

```text
- GitHub PR URL input
- Fetch PR metadata
- Fetch PR diff
- Generate report from PR
```

### Week 4: Backend + Database

Add:

```text
- FastAPI backend
- Save reviews
- Save findings
- Simple review history
```

### Week 5: GitHub App

Add:

```text
- GitHub webhook endpoint
- PR opened/synchronize events
- Post review report as PR comment
```

### Week 6: Dashboard

Add:

```text
- React dashboard
- Review history
- Risk trend
- Finding filters
```

## 15. MVP Success Criteria

Your MVP is successful if it can review a real PR and produce a useful report like:

```text
- 5 clear task requirements
- status for each requirement
- risk score with reasons
- missing test checklist
- 2–5 useful findings
- final merge recommendation
```

Do not measure success by “how many comments it writes.”

Measure success by:

```text
Can this save a developer 10–15 minutes of review time?
Can it catch missing tests?
Can it identify risky AI-generated changes?
Can it tell me where to inspect first?
```

## 16. Resume Bullet After MVP

```text
Built PatchProof, a GitHub-integrated AI PR verification tool that analyzes agent-generated diffs against task specifications, checks requirement completion, flags risky auth/database/API changes, detects missing tests, and generates evidence-based merge-readiness reports.
```

## 17. Startup Direction

Short-term:

```text
A CLI and GitHub PR analyzer for AI-generated code changes.
```

Medium-term:

```text
A GitHub App that comments merge-readiness reports on AI-authored PRs.
```

Long-term:

```text
A trust layer for AI-generated software changes across Cursor, Copilot, Codex, Claude Code, Devin, and future coding agents.
```

The startup wedge is:

```text
AI agents increase code output. PatchProof helps teams decide what is safe to merge.
```
