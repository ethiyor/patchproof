# Phase 8 — Polish, Testing, Deployment & Demo

**Prerequisites:** Phases 1–6 complete (Phase 7 optional but recommended before demo).
**Reference docs:** [08_testing_and_security.md](../08_testing_and_security.md)

---

## Overview

Make the project demo-ready, fully tested, deployed, and documented. This phase turns a working project into a serious portfolio piece.

---

## Milestone 8.1 — Unit Test Coverage

**Goal:** Every core module has unit tests with mocked dependencies.

**Files to create/update:**

```
tests/unit/test_diff_parser.py
tests/unit/test_risk_scorer.py
tests/unit/test_task_analyzer.py
tests/unit/test_verification_engine.py
tests/unit/test_test_checker.py
tests/unit/test_report_generator.py
tests/unit/test_webhook_verifier.py
```

**Tasks:**
- Ensure all 7 sample diff fixtures in `tests/fixtures/sample_diffs/` are tested
- Add golden snapshot test for `report_generator.py` — compare output to `tests/fixtures/golden_reports/`
- Ensure no test calls real OpenAI or real GitHub API
- Run `pytest --cov=core --cov=cli --cov=backend` — aim for >80% coverage on core modules
- Fix all failing tests before moving to next milestone

**Done when:**
```bash
pytest tests/unit/
# All tests pass, no real API calls made
```

---

## Milestone 8.2 — Integration Tests

**Goal:** End-to-end tests for all API endpoints with mocked external services.

**Files to create:**

```
tests/integration/test_reviews_api.py
tests/integration/test_github_webhook.py
tests/mocks/github_api.py  (complete all fixtures)
tests/conftest.py
```

**Tasks:**
- Use `httpx.AsyncClient` with `AsyncTestClient` for API tests
- Use `respx` to mock all outbound HTTP calls (OpenAI, GitHub API)
- Test `POST /reviews/local` end-to-end: request → analysis → database → response
- Test `POST /github/webhook`: valid signature → 202, invalid signature → 403
- Test `GET /reviews/{id}`: existing ID → 200, missing ID → 404
- Use a real PostgreSQL test database (Docker) — separate from dev database

**Done when:**
```bash
pytest tests/integration/
# All tests pass
```

---

## Milestone 8.3 — README & Documentation

**Goal:** A developer can clone the repo and run PatchProof in under 5 minutes.

**Files to create:**

```
README.md
```

**Tasks:**

README sections:
- What PatchProof is (2–3 sentences)
- Demo screenshot or GIF
- Prerequisites: Python 3.12, uv, Docker, OpenAI API key, GitHub token
- Quick start:
  ```bash
  git clone <repo>
  cd patchproof
  cp .env.example .env  # fill in OPENAI_API_KEY
  uv sync
  patchproof review --task task.txt
  ```
- Commands reference: `review`, `review-pr`, with all flags
- Docker Compose quick start for backend + DB
- How to register a GitHub App (link to Phase 5 docs)
- Contributing guide (brief)

**Done when:**
- A fresh clone with the README followed end-to-end produces a working local CLI

---

## Milestone 8.4 — Deployment

**Goal:** Backend + database deployed and accessible from the internet.

**Tasks:**

Option A — Render:
- Create a new Web Service on Render
- Connect GitHub repo
- Set build command: `pip install -r requirements.txt`
- Set start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Add a PostgreSQL database on Render
- Set all env variables: `DATABASE_URL`, `OPENAI_API_KEY`, `GITHUB_TOKEN`, `SECRET_KEY`, `GITHUB_WEBHOOK_SECRET`, `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`
- Run Alembic migration: `alembic upgrade head` (as release command)

Option B — Fly.io:
- `fly launch` → configure `fly.toml`
- `fly postgres create` + `fly secrets set ...`
- `fly deploy`

**Done when:**
- Backend is live at a public URL
- `GET <url>/health` returns `{"status": "ok"}`
- GitHub App webhook points to the deployed URL
- A real PR triggers a PatchProof comment on GitHub

---

## Milestone 8.5 — Demo Video

**Goal:** A 3–5 minute screen recording showing the full workflow.

**Script:**
1. Show a real AI-generated PR (e.g., from Cursor or Copilot Agent)
2. Run `patchproof review-pr <url> --task task.txt` in the terminal
3. Open `patchproof-report.md` and walk through: requirement checklist, risk score, missing tests, reviewer checklist
4. Show the same PR with PatchProof GitHub App — comment auto-posted
5. Open dashboard — show review history and risk trend

**Tools:** OBS Studio, Loom, or macOS screen recording.

**Done when:**
- Video is uploaded to YouTube (unlisted) or Loom
- Link added to README

---

## Phase 8 Acceptance Criteria

```
✓ pytest runs with >80% coverage on core modules
✓ All integration tests pass with mocked external services
✓ README allows a fresh setup in under 5 minutes
✓ Backend deployed to a public URL
✓ GitHub App webhook works end-to-end on deployed URL
✓ Demo video recorded and linked in README
✓ No secrets committed to git history
```

---

## Final Project Checklist

```
✓ Phase 1: patchproof review --task task.txt works
✓ Phase 2: LLM report with requirement checklist and evidence
✓ Phase 3: patchproof review-pr <url> works
✓ Phase 4: Backend + PostgreSQL + Docker Compose
✓ Phase 5: GitHub App posts comments automatically
✓ Phase 6: Dashboard shows review history and risk charts
✓ Phase 8: Tests, deployment, README, demo video
```
