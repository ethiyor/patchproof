"""
Mock LLM response fixtures for all 5 pipeline steps.

Use these in tests by patching llm.client.call_llm to return them directly,
or by building a mock OpenAI response object with the JSON serialised as content.

Never call real OpenAI in unit or integration tests.
"""

# ---------------------------------------------------------------------------
# Step 1 — Extract requirements from task description
# ---------------------------------------------------------------------------

STEP1_REQUIREMENTS = {
    "goal": "Add PDF upload support",
    "requirements": [
        "Create a POST /papers/upload endpoint",
        "Validate MIME type — accept only application/pdf",
        "Enforce a maximum file size of 10MB",
        "Store paper metadata in the database",
        "Return a structured error response for invalid uploads",
    ],
    "expected_test_cases": [
        "valid PDF upload returns 200 with paper_id",
        "non-PDF MIME type is rejected with 400",
        "file exceeding 10MB is rejected with 413",
        "empty file is rejected with 400",
        "backend storage error returns 500",
    ],
    "risk_domains": ["file_upload", "storage", "database", "security"],
}

# ---------------------------------------------------------------------------
# Step 2 — Summarise the diff
# ---------------------------------------------------------------------------

STEP2_DIFF_SUMMARY = {
    "change_summary": (
        "Added a file upload endpoint and a frontend upload form. "
        "A database migration adds the papers table."
    ),
    "implemented_areas": [
        "backend/routes/upload.py — new POST /papers/upload endpoint",
        "frontend/components/PaperUpload.tsx — upload form with drag-and-drop",
    ],
    "possible_side_effects": [
        "Database migration changes the papers table schema",
        "Frontend now sends multipart/form-data requests",
    ],
    "unrelated_changes": [],
}

# ---------------------------------------------------------------------------
# Step 3 — Verify a requirement (two variants)
# ---------------------------------------------------------------------------

STEP3_SATISFIED = {
    "requirement": "Create a POST /papers/upload endpoint",
    "status": "satisfied",
    "evidence": ["backend/routes/upload.py:12 — POST /papers/upload route defined"],
    "reason": "Upload endpoint found in routes file.",
}

STEP3_MISSING = {
    "requirement": "Validate MIME type — accept only application/pdf",
    "status": "missing",
    "evidence": [],
    "reason": (
        "No content_type check found in the upload handler hunk. "
        "The file is saved without validating MIME type."
    ),
}

STEP3_PARTIAL = {
    "requirement": "Return a structured error response for invalid uploads",
    "status": "partially_satisfied",
    "evidence": ["backend/routes/upload.py:28 — returns 400 on missing file"],
    "reason": "Only the missing-file case is handled; MIME and size errors return 500.",
}

# ---------------------------------------------------------------------------
# Step 4 — Risk assessment
# ---------------------------------------------------------------------------

STEP4_RISKS = {
    "risks": [
        {
            "category": "security",
            "severity": "error",
            "title": "No file size limit enforced",
            "description": (
                "The upload endpoint reads the request body without checking "
                "Content-Length or enforcing a maximum body size."
            ),
            "file_path": "backend/routes/upload.py",
            "evidence": "No MAX_UPLOAD_SIZE or size validation found in upload handler.",
        },
        {
            "category": "missing_test",
            "severity": "warning",
            "title": "No test for rejected MIME types",
            "description": "No test case for non-PDF uploads was found in the diff.",
            "file_path": None,
            "evidence": "No test file modified in the diff.",
        },
    ]
}

# ---------------------------------------------------------------------------
# Step 5 — Final report sections (LLM-generated text only)
# ---------------------------------------------------------------------------

STEP5_REPORT_SECTIONS = {
    "executive_summary": (
        "The agent implemented the core upload endpoint and frontend form, "
        "but missed MIME type validation, file size enforcement, and all error-path tests. "
        "This PR is not ready to merge."
    ),
    "suggested_fixes": [
        "Add MAX_UPLOAD_SIZE = 10 * 1024 * 1024 and check Content-Length before reading body",
        "Validate content_type == 'application/pdf' and reject with 400 if not",
        "Add tests/test_upload.py covering the 5 missing test cases",
    ],
    "merge_recommendation": "needs_changes",
}
