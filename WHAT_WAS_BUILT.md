# What Was Built - PatchProof

This file always shows the **latest** milestone. Previous milestones are archived in [`notes/`](notes/).

| Milestone | Note |
|---|---|
| 1.1 - 1.6 - Local CLI | archived in `notes/` |
| 2.1 - 2.7 - LLM Pipeline | archived in `notes/` |
| 3.1 - 3.5 - GitHub PR CLI | archived in `notes/` |
| 4.1 - 4.4 - Backend foundation | archived in `notes/` |
| **4.5 - GitHub PR Review Endpoint** | **current** |

---

## Current: Phase 4 - Milestone 4.5 - POST /reviews/github-pr

### What was built

The FastAPI backend can now review a GitHub pull request by URL.

The new endpoint accepts:

```json
{
  "pr_url": "https://github.com/owner/repo/pull/42",
  "task": "Optional task text"
}
```

It returns the same `ReviewResponse` shape as `/reviews/local`:

```json
{
  "review_id": "...",
  "status": "completed",
  "report_markdown": "# PatchProof Report...",
  "risk_score": 4,
  "risk_level": "medium",
  "merge_recommendation": "needs_changes"
}
```

### Files changed

| File | What changed |
|---|---|
| `backend/schemas/review_schemas.py` | Added `GithubPRReviewRequest` |
| `backend/api/reviews.py` | Added `POST /reviews/github-pr`; extracted shared `_analyze_and_save_review(...)` helper |
| `tests/unit/test_reviews_api.py` | Added GitHub PR endpoint tests |
| `notes/4.5_github_pr_review_endpoint.md` | Deep explanation for this milestone |

### How the endpoint works

```text
1. Validate PR URL format
2. Fetch PR metadata from GitHub
3. Fetch the raw PR diff from GitHub
4. Choose task text from request task, PR body, or linked issue body
5. Reuse PatchProof's parser, risk scorer, optional LLM pipeline, and report generator
6. Get or create Repository and PullRequest rows, then save Review and ChangedFile rows
7. Return ReviewResponse
```

### Why this milestone matters

Phase 3 proved PatchProof can review GitHub PRs from the CLI. Milestone 4.5 turns that ability into an HTTP API so future clients can share the same backend:

```text
VS Code extension / dashboard / GitHub App
  -> POST /reviews/github-pr
  -> backend fetches GitHub data
  -> backend runs PatchProof analysis
  -> backend saves and returns the review
```

### Validation

```bash
.venv/bin/pytest tests/unit/test_reviews_api.py -q
# 28 passed, 1 warning
```

### What comes next - Milestone 4.6

Add `GET /reviews/{review_id}` so saved reviews can be retrieved by ID.
