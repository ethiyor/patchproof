# 08 — Testing Strategy & Security

## Testing Strategy

### Unit Tests

| Module | What to test |
|---|---|
| `diff_parser.py` | Parse added file, deleted file, renamed, binary, empty diff, risky path detection |
| `risk_scorer.py` | Each scoring rule fires correctly; combined score is deterministic |
| `task_analyzer.py` | Mock LLM, verify Pydantic rejects malformed output, verify retry logic |
| `verification_engine.py` | Mock LLM, verify status mapping, verify finding without evidence is rejected |
| `report_generator.py` | Snapshot test — given structured inputs, verify exact Markdown output |
| `api_contract_checker.py` | Field name mismatch is detected; matching fields are not flagged |

### Integration Tests

- **Full pipeline test:** sample diff + sample task → verify report structure is complete and all sections present
- **GitHub client:** use `respx` to mock GitHub API — test PR metadata fetch, diff fetch, 404 handling, rate limit handling
- **FastAPI routes:** use `httpx.AsyncClient` with `AsyncTestClient` — test all endpoint request/response shapes
- **Database:** use a test PostgreSQL instance (Docker) for integration tests; SQLite acceptable for unit-level DB tests

### Sample Diff Fixtures

Store in `tests/fixtures/sample_diffs/`:

| File | Risk level | Description |
|---|---|---|
| `simple_feature_add.diff` | Low | All requirements satisfied, tests present |
| `missing_tests.diff` | Medium | Feature added, no test files changed |
| `auth_change.diff` | High | Touches `auth/` module |
| `payment_change.diff` | Critical | Payment logic changed, no tests |
| `api_contract_break.diff` | High | Backend adds field, frontend not updated |
| `migration_only.diff` | Medium | DB migration with no model update |
| `large_pr.diff` | High | 50+ files changed |
| `unrelated_changes.diff` | Medium | AI changed files outside the task scope |

### Golden Report Snapshots

Store expected report output in `tests/fixtures/golden_reports/`.

On each test run, compare the generated report to the stored snapshot. If different, the test fails and you review the diff manually before updating the snapshot.

Use `pytest-snapshot` or a simple file comparison utility.

### LLM Response Mocking

Never call real OpenAI in unit or integration tests. Patch `llm/client.py` to return stored fixtures.

```python
# tests/mocks/llm_responses.py

MOCK_REQUIREMENTS_OUTPUT = {
    "goal": "Add PDF upload support",
    "requirements": [
        "Create a POST /papers/upload endpoint",
        "Validate MIME type"
    ],
    "expected_test_cases": ["valid PDF upload succeeds", "invalid MIME rejected"],
    "risk_domains": ["file_upload", "security"]
}

MOCK_VERIFICATION_SATISFIED = {
    "requirement": "Create a POST /papers/upload endpoint",
    "status": "satisfied",
    "evidence": ["backend/routes/upload.py:12 — POST /papers/upload defined"],
    "reason": "Upload endpoint found in routes."
}

MOCK_VERIFICATION_MISSING = {
    "requirement": "Validate MIME type",
    "status": "missing",
    "evidence": [],
    "reason": "No content_type check found in the upload handler hunk."
}
```

### GitHub API Mocking

Use `respx` to intercept outbound HTTP calls in tests.

```python
# tests/mocks/github_api.py
# Mock GET /repos/{owner}/{repo}/pulls/{pr_number}
# Mock GET /repos/{owner}/{repo}/pulls/{pr_number}/files
# Mock PR diff endpoint
```

---

## Security Requirements

### GitHub Token Handling

- Store `GITHUB_TOKEN` only in environment variables or `.env` — never hardcode
- Never log the full token — log only the first 4 characters for debugging: `ghp_****`
- Use the minimum required GitHub App permissions (see Phase 5)
- Installation tokens expire in 1 hour — refresh before each use, never cache longer

### OpenAI API Key Handling

- Store `OPENAI_API_KEY` only in environment variables
- Never include API keys in Docker images, git commits, or log output
- Add `.env` to `.gitignore` — commit only `.env.example` with placeholder values

### Webhook Signature Verification

- Always verify `X-Hub-Signature-256` using HMAC-SHA256 before processing any payload
- Reject requests with missing or invalid signatures with `403` immediately
- Use `hmac.compare_digest()` for constant-time comparison — prevents timing attacks

```python
import hmac
import hashlib

def verify_webhook_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)
```

### Minimizing Code Sent to the LLM

- Send only the relevant hunks, not full file contents
- Truncate large diffs to fit the context window — summarize first
- Never send `.env` files, `config/secrets.py`, or files containing keys/passwords to the LLM
- Redact lines matching patterns like `API_KEY=`, `SECRET=`, `PASSWORD=`, `TOKEN=` before sending

```python
SENSITIVE_PATTERNS = [
    r'(?i)(api_key|secret|password|token|credential)\s*=\s*\S+',
]
```

### Minimizing GitHub Repo Access

- GitHub App should only request: `Contents: read`, `Pull requests: read/write`, `Metadata: read`
- CLI should only read the diff and context files — do not traverse the full repo tree
- Do not store raw diff text longer than necessary

### Database Safety

- Use SQLAlchemy ORM with parameterized queries — never build SQL by string concatenation
- Store only what is needed — do not store full repo source code
- Do not store raw `GITHUB_TOKEN` or `OPENAI_API_KEY` in any database row
