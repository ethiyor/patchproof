# 07 — Risk Scoring & Report Format

## Risk Scoring Design

### Hybrid System

```
Final risk score = rule-based score + LLM adjustment (capped ±2)
```

The rule-based score is deterministic and reproducible. The LLM provides a small qualitative adjustment with a reason. This prevents pure-vibes scoring while still capturing context the rules cannot see.

### Rule-Based Scoring Table

| Condition | Points |
|---|---|
| Touches `auth/`, `login/`, `permissions/`, `security/` | +3 |
| Touches `payments/`, `billing/`, `subscriptions/` | +3 |
| Adds or modifies a database migration file | +2 |
| Introduces file upload or user-supplied file handling | +2 |
| Changes public API contract (route added/removed/renamed) | +2 |
| No test files modified at all | +2 |
| Touches `config/`, `.env`, `settings/` | +1 |
| PR has more than 500 lines changed | +1 |
| More than 10 files changed | +1 |
| Touches `middleware/` | +1 |
| Tests added or updated | -2 |
| Documentation updated | -1 |
| CI result passed (if available) | -2 |

### Risk Levels

| Score | Level |
|---|---|
| 0–2 | 🟢 Low |
| 3–5 | 🟡 Medium |
| 6–8 | 🔴 High |
| 9+ | 🚨 Critical |

### Example Score Output

```json
{
  "rule_score": 8,
  "llm_adjustment": -1,
  "final_score": 7,
  "risk_level": "high",
  "reasons": [
    "File upload introduced (+2)",
    "Database migration modified (+2)",
    "No test files changed (+2)",
    "Config file touched (+1)",
    "LLM: upload path validation is present but incomplete (-1)"
  ]
}
```

### Merge Recommendation Logic

| Condition | Recommendation |
|---|---|
| All requirements satisfied, risk Low, tests present | `ready` |
| All requirements satisfied, risk Low/Medium, minor issues | `ready_with_comments` |
| 1+ requirements missing OR risk High | `needs_changes` |
| Critical risk OR security finding of critical severity | `do_not_merge` |

---

## Report Format

This is the full Markdown report structure. Every section must be present. Every finding must cite a file path and a reason.

```markdown
# PatchProof Report

**Repository:** papermind
**Branch / PR:** feat/pdf-upload
**Task:** Add PDF upload support with MIME validation and file size limits.
**Generated:** 2026-07-03 10:00 UTC

---

## Executive Summary

The AI agent implemented the core upload endpoint and frontend form, but missed
MIME type validation, file size enforcement, and all error-path tests.
This PR is not ready to merge in its current state.

---

## Merge Readiness

| Field | Value |
|---|---|
| Risk level | 🔴 High (score: 7) |
| Merge recommendation | **Needs changes** |

---

## Task Completion Checklist

| Requirement | Status | Evidence |
|---|---|---|
| Create POST /papers/upload endpoint | ✅ Satisfied | backend/routes/upload.py:12 |
| Validate MIME type | ❌ Missing | No MIME check found in upload handler |
| Enforce file size limit | ❌ Missing | No Content-Length or size check found |
| Store paper metadata | ✅ Satisfied | backend/models/paper.py:34 |
| Return structured error responses | ⚠️ Partially satisfied | Success handled, error path missing |

---

## Risk Score

**Score: 7 / High**

| Reason | Points |
|---|---|
| File upload introduced | +2 |
| Database migration modified | +2 |
| No test files changed | +2 |
| Config file touched | +1 |

---

## Risky Files Touched

| File | Risk category |
|---|---|
| `backend/routes/upload.py` | File upload — no size or MIME validation |
| `migrations/003_papers.sql` | Database migration — schema change |
| `backend/services/storage.py` | Writes user files to disk |

---

## Missing Tests

Expected test cases not found in the diff:

- [ ] Valid PDF upload returns 200 with paper_id
- [ ] Non-PDF MIME type rejected with 400
- [ ] File exceeding 10MB rejected with 413
- [ ] Empty file rejected with 400
- [ ] Backend storage error returns 500

---

## Possible Bugs

**1. No file size limit — `backend/routes/upload.py`**
The upload handler reads the request body without enforcing a maximum size.
An attacker or misconfigured client could upload arbitrarily large files.

**2. MIME type not validated — `backend/routes/upload.py`**
The endpoint accepts any file type. A non-PDF will be stored and may cause
errors downstream when the PDF parser processes it.

---

## API / Database / Security Concerns

- **API contract mismatch:** Frontend reads `response.data.id` but backend returns `paper_id`.
  This will cause a silent failure in the upload success handler.
  Frontend: `frontend/components/PaperUpload.tsx:47`
  Backend: `backend/routes/upload.py:31`

- **Authentication missing:** No auth check on the upload endpoint.
  Any unauthenticated user can upload files.

---

## Human Reviewer Checklist

Inspect the following before approving:

1. `backend/routes/upload.py` — verify size limit and MIME check are added
2. `backend/services/storage.py` — verify error handling for failed writes
3. `frontend/components/PaperUpload.tsx` — verify error state is rendered
4. `migrations/003_papers.sql` — verify rollback is safe

---

## Suggested Fixes

1. Add `MAX_UPLOAD_SIZE = 10 * 1024 * 1024` and check `Content-Length` before reading body
2. Validate `content_type == "application/pdf"` and reject with 400 if not
3. Fix frontend to read `response.data.paper_id` (not `response.data.id`)
4. Add authentication dependency to the upload route
5. Add `tests/test_upload.py` covering the 5 missing test cases above

---

## Final Recommendation

> **Needs changes** — 2 security gaps (no size limit, no MIME validation),
> 5 missing tests, 1 API contract mismatch, 1 missing auth check.
> Fix the above before merging.
```

---

## Evidence Rule

Every finding in the report must follow this rule:

**Bad (not allowed):**
```
This code may be insecure.
```

**Good (required):**
```
File upload endpoint accepts user files without checking MIME type or file size.
File: backend/routes/upload.py — no content_type check or Content-Length limit found in the upload handler.
```

Prefer 2–5 high-confidence findings over 10 vague ones.
