# What Was Built - PatchProof

This file always shows the **latest** milestone. Previous milestones are archived in [`notes/`](notes/).

| Milestone | Note |
|---|---|
| 1.1 - 1.6 - Local CLI | archived in `notes/` |
| 2.1 - 2.7 - LLM Pipeline | archived in `notes/` |
| 3.1 - 3.5 - GitHub PR CLI | archived in `notes/` |
| 4.1 - 4.4 - Backend foundation | archived in `notes/` |
| 4.5 - GitHub PR Review Endpoint | archived in `notes/` |
| **4.6 - Get Review Endpoint** | **current** |

---

## Current: Phase 4 - Milestone 4.6 - GET /reviews/{review_id}

### What was built

The FastAPI backend can now retrieve a saved review by ID.

After a client creates a review through `POST /reviews/local` or
`POST /reviews/github-pr`, it can use the returned `review_id` to fetch the
stored review details later.

The new endpoint is:

```text
GET /reviews/{review_id}
```

It returns a `ReviewDetailResponse`:

```json
{
  "review_id": "...",
  "created_at": "2026-07-06T12:30:00Z",
  "task_text": "Add PDF upload validation",
  "risk_score": 4,
  "risk_level": "medium",
  "merge_recommendation": "needs_changes",
  "report_markdown": "# PatchProof Report...",
  "findings": [],
  "requirement_checks": [],
  "changed_files": []
}
```

### Files changed

| File | What changed |
|---|---|
| `backend/schemas/review_schemas.py` | Added `ReviewDetailResponse` and nested response schemas |
| `backend/api/reviews.py` | Added `GET /reviews/{review_id}` |
| `tests/unit/test_reviews_api.py` | Added review detail and not-found tests |
| `notes/4.6_get_review_endpoint.md` | Deep explanation for this milestone |

### How the endpoint works

```text
1. Validate `review_id` as a UUID
2. Query the `reviews` table by ID
3. Load related findings, requirement checks, and changed files
4. Return one full saved review response
5. Return `404` if the review does not exist
```

### Why this milestone matters

Milestones 4.4 and 4.5 made the backend create and store reviews. Milestone 4.6
adds the matching read path:

```text
client creates review
  -> backend returns review_id
  -> client later calls GET /reviews/{review_id}
  -> backend returns the saved report and related details
```

### Validation

```bash
python -m compileall backend tests/unit/test_reviews_api.py
# Compilation succeeded
```

`pytest` could not be run in this local environment because the active Python does not have `pytest` installed.

### What comes next - Milestone 4.7

Update the CLI so it can call the backend instead of only running analysis in-process.


I wrote this sentence just to make changes.