# Phase 3 — GitHub PR Fetching

**Prerequisites:** Phase 2 complete. `patchproof review` produces a full LLM report.
**Reference docs:** [05_data_models_and_api.md](../05_data_models_and_api.md), [08_testing_and_security.md](../08_testing_and_security.md)

---

## Overview

Add a `review-pr` command that accepts a GitHub PR URL, fetches the diff and metadata automatically, and runs the same analysis pipeline as the local CLI.

---

## Milestone 3.1 — GitHub Client Setup & Auth

**Goal:** A reusable GitHub API client that authenticates with a personal access token.

**Files to create:**

```
cli/github_client.py
tests/mocks/github_api.py
```

**Tasks:**
- Read `GITHUB_TOKEN` from environment — raise a clear error if missing
- Create `GitHubClient` class with base URL `https://api.github.com`
- Add `get` method using `httpx.AsyncClient` with:
  - `Authorization: Bearer {token}` header
  - `Accept: application/vnd.github+json` header
  - `X-GitHub-Api-Version: 2022-11-28` header
  - Timeout of 30 seconds
- Handle errors: 401 (bad token), 403 (rate limit), 404 (not found)
- Never log the full token — only first 4 chars for debug: `ghp_****`
- Create `tests/mocks/github_api.py` with `respx` fixtures for all endpoints

**Done when:**
- Client can make a real authenticated call to `GET /user` and return the response
- Mock-based test passes with a fake token

---

## Milestone 3.2 — PR Metadata Fetching

**Goal:** Fetch all PR metadata needed for the analysis.

**Files to modify:**

```
cli/github_client.py
models/github_models.py  (new)
tests/unit/test_github_client.py  (new)
```

**Tasks:**
- Parse a GitHub PR URL into `owner`, `repo`, `pr_number` using regex
- Fetch: `GET /repos/{owner}/{repo}/pulls/{pr_number}`
- Extract: `title`, `body`, `user.login`, `base.ref`, `head.ref`, `state`
- Fetch linked issue: if PR body contains `Closes #N` or `Fixes #N`, fetch `GET /repos/{owner}/{repo}/issues/{N}`
- Return: `PRMetadata` Pydantic model

**Done when:**
- Mock test passes: given a PR URL, returns correct `PRMetadata`
- Invalid URL raises a clear error: `"Invalid GitHub PR URL format"`

---

## Milestone 3.3 — PR Diff Fetching

**Goal:** Fetch the raw unified diff for the PR.

**Files to modify:**

```
cli/github_client.py
tests/unit/test_github_client.py
tests/fixtures/sample_diffs/github_pr.diff  (new)
```

**Tasks:**
- Fetch diff: `GET /repos/{owner}/{repo}/pulls/{pr_number}` with header `Accept: application/vnd.github.diff`
- Return raw diff text string
- Handle empty diff (no file changes) gracefully
- Store a real fetched diff as `tests/fixtures/sample_diffs/github_pr.diff` for future tests
- Handle pagination if PR has more than 300 files (GitHub API file list limit)

**Done when:**
- Mock test passes: given a PR number, returns a raw unified diff string
- Empty diff returns an empty string with no crash

---

## Milestone 3.4 — `review-pr` CLI Command

**Goal:** Wire everything together into the `patchproof review-pr` command.

**Files to modify:**

```
cli/main.py
```

**Tasks:**
- Add `review-pr` Typer command: `patchproof review-pr <pr_url> --task task.txt`
- If `--task` not provided, use PR body as task (fallback to linked issue body)
- If PR body is empty and no `--task` provided, show error: `"Provide a task with --task or add a description to the PR body"`
- Fetch PR metadata + diff using `GitHubClient`
- Run the same analysis pipeline as `review` command
- Write `patchproof-report.md` same as before
- Print summary to terminal: `"Fetched PR #42: Add PDF upload support (6 files, +243 -31)"`

**Done when:**
```bash
patchproof review-pr https://github.com/user/repo/pull/42 --task task.txt
# Fetched PR #42: Add PDF upload support
# Collected diff: 6 files changed (+243 -31)
# Report written to patchproof-report.md
```

---

## Milestone 3.5 — End-to-End Test on a Real PR

**Goal:** Verify the full `review-pr` workflow works on a real GitHub PR.

**Tasks:**
- Pick a real PR from one of your projects (or create a test PR)
- Run `patchproof review-pr <url> --task task.txt` with `GITHUB_TOKEN` set
- Read the report and verify it reflects the actual PR changes
- Check: correct files listed, risk flags match, requirements make sense
- Fix any bugs or prompt issues
- Update `tests/fixtures/sample_diffs/github_pr.diff` with a real fetched diff

**Done when:**
- `review-pr` works on a real public PR end-to-end
- Report quality is comparable to the local CLI output

---

## Phase 3 Acceptance Criteria

```
✓ patchproof review-pr <url> --task task.txt works on a real GitHub PR
✓ PR body can be used as task if --task not provided
✓ GitHub token errors (missing, expired, rate limit) give clear messages
✓ Invalid PR URL gives a clear error
✓ Report quality is the same as local CLI review
✓ Mock-based tests pass for PR metadata fetch and diff fetch
✓ GITHUB_TOKEN never logged in full
```
