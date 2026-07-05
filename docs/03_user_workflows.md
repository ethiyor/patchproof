# 03 — User Workflows

## Workflow 1: Local CLI (MVP — Phase 1 + 2)

```
Developer runs AI agent to complete a task
         │
         ▼
Developer writes task description to task.txt
         │
         ▼
Developer runs: patchproof review --task task.txt
         │
         ▼
CLI detects Git repo root, collects diff from working tree
         │
         ▼
Diff parser extracts: file list, hunks, additions, deletions, risky paths
         │
         ▼
Task analyzer extracts: requirements, expected tests, risk domains
         │
         ▼
LLM pipeline runs (5 steps)
         │
         ▼
Risk scoring engine computes score
         │
         ▼
Report generator writes patchproof-report.md
         │
         ▼
Developer reads report and decides whether to push or fix first
```

**Commands:**

```bash
patchproof review --task task.txt
patchproof review --staged --task task.txt
patchproof review --diff saved.diff --task task.txt
```

---

## Workflow 2: GitHub PR Analyzer (Phase 3)

```
Developer runs: patchproof review-pr <github-pr-url> --task task.txt
         │
         ▼
GitHub client parses PR URL (owner, repo, PR number)
         │
         ▼
GitHub client fetches PR metadata: title, body, author, branches
         │
         ▼
GitHub client fetches PR diff using application/vnd.github.diff
         │
         ▼
If no task.txt provided, use PR body or linked issue as task
         │
         ▼
Same pipeline as local CLI runs on the fetched diff
         │
         ▼
patchproof-report.md written locally
```

**Command:**

```bash
patchproof review-pr https://github.com/org/repo/pull/42 --task task.txt
```

---

## Workflow 3: GitHub App — Automated (Phase 5)

```
Developer opens or updates a PR
         │
         ▼
GitHub sends webhook event (pull_request: opened or synchronize)
         │
         ▼
PatchProof backend verifies webhook signature (HMAC-SHA256)
         │
         ▼
Backend responds 202 immediately (non-blocking)
         │
         ▼
Background task: fetch PR diff using installation access token
         │
         ▼
Task extracted from PR body or linked issue
         │
         ▼
Same analysis pipeline runs
         │
         ▼
Report posted as a PR comment via GitHub API
```

---

## Workflow 4: VS Code / Cursor Extension (Phase 7 — future)

```
Developer finishes a Cursor or Copilot Agent session
         │
         ▼
Extension detects uncommitted changes in the workspace
         │
         ▼
Developer types task description in the sidebar input panel
         │
         ▼
Extension collects diff from VS Code Git API
         │
         ▼
Extension calls PatchProof backend with diff + task
         │
         ▼
Report displayed inline in VS Code sidebar
         │
         ▼
Risky files highlighted in the file explorer
```

---

## Report Output (All Workflows)

Every workflow produces the same report sections:

```
✓ Executive summary
✓ Merge readiness (risk level + recommendation)
✓ Task completion checklist (satisfied / missing / unclear per requirement)
✓ Risk score with reasons
✓ Risky files touched (with risk category per file)
✓ Missing tests checklist (expected cases not found)
✓ Possible bugs (evidence-backed only)
✓ API / database / security concerns
✓ Human reviewer checklist (exactly which files to inspect)
✓ Suggested fixes
✓ Final recommendation: Ready / Ready with comments / Needs changes / Do not merge
```
