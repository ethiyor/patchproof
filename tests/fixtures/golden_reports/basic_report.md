# PatchProof Report

**Repository:** test-repo  
**Branch:** test-branch  
**Task:** Update JWT token expiry and add IAT claim.  
**Generated:** 2026-07-05 00:00 UTC  

---

## Merge Readiness

| Field | Value |
|---|---|
| Risk score | 5 |
| Risk level | 🟡 Medium |

---

## Risk Score Details

**Reasons:**

- Touches auth/security (auth) (+3)
- No test files changed (+2)

---

## Risky Files

| File | Risk flags |
|---|---|
| `backend/auth/jwt_handler.py` | auth |

---

## Changed Files

| File | Status | Language | +Added | -Removed |
|---|---|---|---|---|
| `backend/auth/jwt_handler.py` | modified | python | +2 | -2 |
| **Total** | | | **+2** | **-2** |

---

## Task Completion Checklist

> ⚠️ LLM analysis coming in Phase 2. This section will verify each requirement against the diff.

---

## Missing Tests

> ⚠️ LLM analysis coming in Phase 2. This section will list expected test cases not found in the diff.

---

## Final Recommendation

> ⚠️ LLM analysis coming in Phase 2. This section will give a merge recommendation with evidence.
