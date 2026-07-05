# 06 — LLM Pipeline

The LLM pipeline is split into 5 focused steps. Never use one giant prompt for the entire analysis — each step does one thing and its output is validated with Pydantic before the next step runs.

All prompts use structured output mode (JSON). Temperature is set to 0.1 for determinism.

---

## Step 1: Extract Requirements from Task

**Purpose:** Convert the task description into a concrete, checkable requirement list.

**Input:**

```text
Task description text.
Example: "Add PDF upload support with MIME validation and a 10MB file size limit."
```

**Output shape:**

```json
{
  "goal": "Add PDF upload support",
  "requirements": [
    "Create a POST /papers/upload endpoint",
    "Validate MIME type — accept only application/pdf",
    "Enforce a maximum file size of 10MB",
    "Store paper metadata in the database",
    "Return a structured error response for invalid uploads"
  ],
  "expected_test_cases": [
    "valid PDF upload returns 200 with paper_id",
    "non-PDF MIME type is rejected with 400",
    "file exceeding 10MB is rejected with 413",
    "empty file is rejected with 400",
    "backend storage error returns 500 with error message"
  ],
  "risk_domains": ["file_upload", "storage", "database", "security"]
}
```

**Failure cases:**
- LLM returns empty requirements → retry once, then fail with a user-facing message asking for a more specific task
- LLM invents requirements not in the task → validate with instruction below

**Hallucination reduction:**
- Prompt: *"Only extract requirements explicitly stated or strongly implied by the task. Do not invent requirements."*
- Temperature: 0.1

---

## Step 2: Summarize the Diff

**Purpose:** Produce a human-readable summary of what actually changed in the diff.

**Input:**

```text
List of changed files with their hunks.
Truncate large diffs to fit context window — summarize large files before sending.
```

**Output shape:**

```json
{
  "change_summary": "Added a file upload endpoint, a frontend upload form, and a database model for papers.",
  "implemented_areas": [
    "backend/routes/upload.py — new POST /papers/upload endpoint",
    "frontend/components/PaperUpload.tsx — upload form with drag-and-drop"
  ],
  "possible_side_effects": [
    "Database migration changes the papers table schema",
    "Frontend now sends multipart/form-data requests"
  ],
  "unrelated_changes": [
    "frontend/components/Navbar.tsx — unrelated style tweak"
  ]
}
```

**Failure cases:**
- Diff too large for context window → chunk by file, summarize each, merge summaries

**Hallucination reduction:**
- Prompt: *"Summarize only what is actually present in the diff. Reference specific file paths. Do not assume what the code does beyond what is shown."*

---

## Step 3: Verify Each Requirement

**Purpose:** For each requirement from Step 1, determine whether the diff satisfies it, with evidence.

**Input (called once per requirement):**

```json
{
  "requirement": "Validate MIME type — accept only application/pdf",
  "relevant_diff": "... hunk from backend/routes/upload.py ...",
  "repo_context": "... content of backend/services/storage.py ..."
}
```

**Output shape:**

```json
{
  "requirement": "Validate MIME type — accept only application/pdf",
  "status": "missing",
  "evidence": [],
  "reason": "The upload endpoint in backend/routes/upload.py saves the file directly without checking the content_type header or file extension."
}
```

**Statuses:**

| Status | Meaning |
|---|---|
| `satisfied` | Clear evidence the requirement is implemented |
| `partially_satisfied` | Partially implemented — some but not all aspects covered |
| `missing` | No evidence of implementation in the diff |
| `unclear` | Diff is ambiguous or context is insufficient to determine |
| `out_of_scope_change` | A change was made that is unrelated to this requirement |

**Failure cases:**
- `satisfied` returned with no evidence → reject, retry once requesting evidence
- `missing` returned with no reason → reject, retry once requesting reason

**Hallucination reduction:**
- Prompt: *"If you cannot find evidence in the diff or context provided, mark the status as 'missing' or 'unclear'. Do not assume evidence exists outside the provided content."*
- Require `evidence` field (list of file + line citations) for any `satisfied` or `partially_satisfied` status.

---

## Step 4: Detect Risky Changes

**Purpose:** Identify security, integrity, and correctness risks in the diff beyond the requirement checklist.

**Input:**

```json
{
  "risk_flags": ["file_upload", "database_migration"],
  "diff_summary": "...",
  "changed_files": [
    { "path": "backend/routes/upload.py", "risk_flags": ["file_upload"] },
    { "path": "migrations/003_papers.sql", "risk_flags": ["migration"] }
  ]
}
```

**Output shape:**

```json
{
  "risks": [
    {
      "category": "security",
      "severity": "error",
      "title": "No file size limit enforced",
      "description": "The upload endpoint does not check Content-Length or enforce a maximum body size. This allows unbounded file uploads.",
      "file_path": "backend/routes/upload.py",
      "evidence": "No MAX_UPLOAD_SIZE or size validation check found in the upload handler hunk."
    },
    {
      "category": "missing_test",
      "severity": "warning",
      "title": "No test for rejected MIME types",
      "description": "The expected test case for non-PDF uploads is not present in any test file in the diff.",
      "file_path": null,
      "evidence": "No test file modified in the diff."
    }
  ]
}
```

**Failure cases:**
- Risk returned without a `file_path` or `evidence` → reject that individual finding, do not include in report

**Hallucination reduction:**
- Prompt: *"Only report risks you can directly support with evidence from the provided diff. Do not speculate. Prefer 2–3 high-confidence risks over 10 vague ones."*

---

## Step 5: Generate Final Report Sections

**Purpose:** Assemble all structured outputs into the executive summary and suggested fixes sections of the final report. The other sections are populated directly from structured data, not by the LLM.

**Input:**

```json
{
  "requirement_checks": [...],
  "risk_score": 7,
  "risk_level": "high",
  "risks": [...],
  "missing_tests": [...],
  "api_contract_issues": [...],
  "diff_summary": "...",
  "task": "..."
}
```

**Output shape:**

```json
{
  "executive_summary": "The AI agent implemented the core upload endpoint and frontend form, but missed MIME type validation, file size enforcement, and all error-path tests. This PR is not ready to merge.",
  "suggested_fixes": [
    "Add MAX_UPLOAD_SIZE = 10 * 1024 * 1024 and check Content-Length before reading the body",
    "Validate content_type == 'application/pdf' and reject with 400 if not",
    "Fix frontend to read response.data.paper_id (not response.data.id)",
    "Add tests/test_upload.py covering the 5 missing test cases"
  ],
  "merge_recommendation": "needs_changes"
}
```

**Note:** This step is mostly a template-render operation. Only the executive summary and suggested fixes are LLM-generated. All checklist sections are populated from structured data to minimize hallucination.

---

## Pipeline Orchestration

```
task_text + diff_text + repo_context
         │
         ▼
Step 1 → RequirementsOutput (Pydantic)
         │
         ▼
Step 2 → DiffSummaryOutput (Pydantic)
         │
         ▼
Step 3 → [VerificationResult] × len(requirements) (parallel safe)
         │
         ▼
Step 4 → RiskAssessmentOutput (Pydantic)
         │
         ▼
Rule-based risk score + LLM score combined
         │
         ▼
Step 5 → FinalReportSections (Pydantic)
         │
         ▼
report_generator.py assembles all into patchproof-report.md
```

Step 3 verifications can be run in parallel (one LLM call per requirement) to reduce total pipeline latency.
