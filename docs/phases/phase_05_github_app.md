# Phase 5 — GitHub App + Webhooks

**Prerequisites:** Phase 4 complete. Backend is running with PostgreSQL.
**Reference docs:** [05_data_models_and_api.md](../05_data_models_and_api.md), [08_testing_and_security.md](../08_testing_and_security.md)

---

## Overview

Register PatchProof as a GitHub App. When a pull request is opened or updated, GitHub sends a webhook. PatchProof verifies the signature, fetches the PR diff, runs the analysis in the background, and posts the report as a PR comment.

---

## Milestone 5.1 — GitHub App Registration & Config

**Goal:** A registered GitHub App with the minimum required permissions and a local tunnel for testing.

**Tasks:**
- Go to GitHub → Settings → Developer Settings → GitHub Apps → New GitHub App
- Set permissions:
  - Contents: Read
  - Pull requests: Read and Write
  - Issues: Read
  - Metadata: Read (mandatory)
- Subscribe to events: `pull_request`
- Set webhook URL to your `ngrok` or Cloudflare Tunnel URL + `/github/webhook`
- Download the private key (`.pem` file) — store securely, add to `.gitignore`
- Add to `.env.example`: `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY_PATH`, `GITHUB_WEBHOOK_SECRET`
- Install `ngrok` or `cloudflared` for local webhook testing

**Done when:**
- GitHub App is registered and visible in your GitHub account
- `.env` has `GITHUB_APP_ID` and private key path set
- Tunnel is running and forwarding to `localhost:8000`

---

## Milestone 5.2 — Webhook Endpoint with Signature Verification

**Goal:** A secure endpoint that receives GitHub PR events and rejects invalid requests.

**Files to create:**

```
backend/api/github_webhook.py
backend/services/webhook_verifier.py
tests/unit/test_webhook_verifier.py
```

**Tasks:**
- Implement `POST /github/webhook` endpoint
- Read raw request body (must be raw bytes for HMAC — do not parse JSON first)
- Verify `X-Hub-Signature-256` header using `hmac.compare_digest` (constant-time)

```python
import hmac, hashlib

def verify_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)
```

- If signature missing or invalid → return `403` immediately, do not process
- If `X-GitHub-Event` is not `pull_request` → return `200` (ignore other events)
- Return `202 Accepted` immediately for valid `pull_request` events

**Done when:**
- A request with a correct HMAC signature is accepted
- A request with a wrong signature returns `403`
- Unit test covers both cases

---

## Milestone 5.3 — JWT Auth + Installation Access Token

**Goal:** Authenticate as the GitHub App and exchange for an installation access token.

**Files to create:**

```
backend/services/github_app.py
tests/unit/test_github_app.py
```

**Tasks:**
- Generate a JWT signed with the App's private key (`PyJWT` or `jwt` library):
  - `iss`: App ID
  - `iat`: now
  - `exp`: now + 60 seconds
  - Algorithm: `RS256`
- Use the JWT to call `POST /app/installations/{installation_id}/access_tokens`
- Return: `installation_token` string (expires in 1 hour)
- Cache the token per `installation_id` with expiry — refresh when less than 60 seconds remain
- Never store the installation token in the database

**Done when:**
- Given a real `installation_id`, returns a valid installation access token
- Token is refreshed automatically when close to expiry
- Mock-based unit test passes

---

## Milestone 5.4 — Background Task + PR Analysis

**Goal:** When a valid webhook arrives, fetch the PR diff and run analysis in the background.

**Files to modify:**

```
backend/api/github_webhook.py
backend/services/github_app.py
```

**Tasks:**
- Extract `installation.id`, `repository.full_name`, `pull_request.number`, and `pull_request.body` from webhook payload
- Use `FastAPI BackgroundTasks` to schedule the analysis task (non-blocking response)
- Background task:
  1. Get installation token for `installation_id`
  2. Fetch PR diff using installation token
  3. Use PR body as task (or linked issue body if PR body is empty)
  4. Run analysis pipeline
  5. Save review to database
  6. Trigger Milestone 5.5 to post the comment

**Done when:**
- Webhook arrives → `202` returned immediately
- Review is saved to the database within 30 seconds
- Check database: `SELECT * FROM reviews ORDER BY created_at DESC LIMIT 1`

---

## Milestone 5.5 — Post Report as PR Comment

**Goal:** After analysis completes, post the Markdown report as a comment on the PR.

**Files to create:**

```
backend/services/pr_commenter.py
tests/unit/test_pr_commenter.py
```

**Tasks:**
- Implement `POST /reviews/{review_id}/comment` endpoint
- Use installation token to call `POST /repos/{owner}/{repo}/issues/{pr_number}/comments` with the report Markdown
- Format report for GitHub: ensure headers, tables, and code blocks render correctly
- Handle failure: if comment posting fails, log the error but do not retry infinitely
- Return the `comment_url` from GitHub API response

**Done when:**
- After a PR is opened, a PatchProof comment appears on the PR within 30 seconds
- The comment contains the full report with all sections

---

## Milestone 5.6 — End-to-End Test

**Goal:** Verify the full GitHub App flow works on a real test repository.

**Tasks:**
- Create a test repo on GitHub (can be private)
- Install the PatchProof GitHub App on it
- Make a branch, push a change, open a PR
- Verify: PatchProof comment appears with the correct report
- Test the `synchronize` event: push another commit to the PR, verify a new comment appears
- Fix any bugs found

**Done when:**
- Opening a PR on the test repo → PatchProof comment with full report appears within 30 seconds
- Updating the PR triggers a new analysis

---

## Phase 5 Acceptance Criteria

```
✓ Webhook signature verification rejects invalid signatures (403)
✓ Valid webhook triggers analysis in background (202 returned immediately)
✓ Installation access token obtained and cached correctly
✓ PR comment posted with full report after analysis
✓ pull_request opened and synchronize events both trigger analysis
✓ Private key path never committed — only in .env
✓ GITHUB_WEBHOOK_SECRET never logged
✓ Unit tests for signature verification and JWT generation
```
