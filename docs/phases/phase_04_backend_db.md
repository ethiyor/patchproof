# Phase 4 — FastAPI Backend + PostgreSQL

**Prerequisites:** Phase 3 complete. `review-pr` works end-to-end.
**Reference docs:** [05_data_models_and_api.md](../05_data_models_and_api.md), [04_architecture.md](../04_architecture.md)

---

## Overview

Move the analysis engine into a FastAPI backend server. Persist reviews to PostgreSQL. Update the CLI to POST to the backend instead of running analysis in-process.

---

## Milestone 4.1 — FastAPI App Scaffold

**Goal:** A running FastAPI app with a health check endpoint.

**Files to create:**

```
backend/__init__.py
backend/main.py
backend/config.py
requirements-backend.txt  (or add to pyproject.toml)
```

**Tasks:**
- Create FastAPI app with `lifespan` context manager
- Add `GET /health` endpoint returning `{"status": "ok"}`
- Add `pydantic-settings` config class: reads `DATABASE_URL`, `OPENAI_API_KEY`, `GITHUB_TOKEN`, `SECRET_KEY` from env
- Run with `uvicorn backend.main:app --reload`
- Add `backend/` to project structure (alongside `cli/` and `core/`)

**Done when:**
```bash
uvicorn backend.main:app --reload
# GET /health → {"status": "ok"}
```

---

## Milestone 4.2 — SQLAlchemy Async Models

**Goal:** Define all ORM models matching the schema in [05_data_models_and_api.md](../05_data_models_and_api.md).

**Files to create:**

```
backend/db/__init__.py
backend/db/models.py
backend/db/session.py
```

**Tasks:**
- Create async SQLAlchemy engine using `DATABASE_URL` from config
- Create `AsyncSession` factory
- Define ORM models for all 7 tables: `User`, `Repository`, `PullRequest`, `Review`, `ReviewFinding`, `RequirementCheck`, `ChangedFile`
- Use `UUID` primary keys with `gen_random_uuid()`
- Use `ARRAY(String)` for `risk_flags` on `ChangedFile`
- Add `__repr__` for debug-friendly output

**Done when:**
- Models import without errors
- `session.py` creates an async session factory successfully

---

## Milestone 4.3 — Alembic Migrations

**Goal:** Set up Alembic and create the initial migration for all tables.

**Files to create:**

```
backend/db/migrations/env.py
backend/db/migrations/versions/001_initial_schema.py
alembic.ini
```

**Tasks:**
- `alembic init backend/db/migrations`
- Configure `env.py` to use async engine and import all models
- Generate initial migration: `alembic revision --autogenerate -m "initial schema"`
- Review generated SQL — verify all tables, types, and constraints are correct
- Apply migration: `alembic upgrade head`
- Verify all tables exist in the database

**Done when:**
```bash
alembic upgrade head
# All 7 tables created in PostgreSQL
```

---

## Milestone 4.4 — POST `/reviews/local` Endpoint

**Goal:** The CLI can POST a diff + task to the backend and get back a report.

**Files to create:**

```
backend/api/__init__.py
backend/api/reviews.py
backend/schemas/review_schemas.py
```

**Tasks:**
- Define `LocalReviewRequest` and `ReviewResponse` Pydantic schemas (see [05_data_models_and_api.md](../05_data_models_and_api.md))
- Implement `POST /reviews/local`:
  1. Validate request body
  2. Run the same analysis pipeline (imported from `core/`)
  3. Save `Review` + `ReviewFinding` + `RequirementCheck` + `ChangedFile` rows to database
  4. Return `ReviewResponse` with `review_id`, `report_markdown`, `risk_score`, `merge_recommendation`
- Add the router to `backend/main.py`
- Integration test with `httpx.AsyncClient`

**Done when:**
```bash
curl -X POST /reviews/local -d '{"task": "...", "diff": "..."}'
# Returns review_id and report_markdown
# Row saved in reviews table
```

---

## Milestone 4.5 — POST `/reviews/github-pr` Endpoint

**Goal:** The backend can fetch and analyze a GitHub PR by URL.

**Files to modify:**

```
backend/api/reviews.py
backend/schemas/review_schemas.py
```

**Tasks:**
- Define `GithubPRReviewRequest` schema: `pr_url`, `task` (optional)
- Implement `POST /reviews/github-pr`:
  1. Validate PR URL format
  2. Use `GitHubClient` to fetch PR metadata + diff
  3. Use PR body as task if `task` not provided
  4. Run analysis pipeline
  5. Save to database
  6. Return `ReviewResponse`

**Done when:**
```bash
curl -X POST /reviews/github-pr -d '{"pr_url": "https://github.com/.../pull/42"}'
# Returns report for that PR
```

---

## Milestone 4.6 — GET `/reviews/{review_id}` Endpoint

**Goal:** Retrieve a saved review by ID.

**Files to modify:**

```
backend/api/reviews.py
```

**Tasks:**
- Implement `GET /reviews/{review_id}`
- Fetch `Review` + related `ReviewFinding` + `RequirementCheck` rows
- Return full `ReviewDetailResponse` schema
- Return `404` with a clear message if review not found

**Done when:**
- A review created in milestone 4.4 can be fetched by its ID
- Unknown ID returns `{"detail": "Review not found"}` with 404

---

## Milestone 4.7 — Update CLI to Call Backend

**Goal:** The CLI POSTs to the local backend instead of running analysis in-process.

**Files to modify:**

```
cli/main.py
cli/config_loader.py
```

**Tasks:**
- Add `PATCHPROOF_API_URL` to config (default: `http://localhost:8000`)
- If `PATCHPROOF_API_URL` is set: POST to `/reviews/local` and write returned `report_markdown` to disk
- If not set (offline mode): run analysis in-process as before (Phase 1–2 behaviour)
- Print `review_id` to terminal: `"Review saved: rev_abc123"`

**Done when:**
- With backend running: `patchproof review --task task.txt` POSTs to backend and writes the returned report
- Without backend: falls back to in-process analysis

---

## Milestone 4.8 — Docker Compose for Local Dev

**Goal:** One command to start the full local dev environment.

**Files to create:**

```
docker-compose.yml
Dockerfile.backend
```

**Tasks:**
- `docker-compose.yml` services: `backend` (FastAPI), `db` (PostgreSQL 16)
- Backend service mounts source code, runs `uvicorn` with `--reload`
- DB service uses named volume for persistence
- Add `db` health check so backend waits for Postgres to be ready
- Document in README: `docker compose up`

**Done when:**
```bash
docker compose up
# Backend at http://localhost:8000
# PostgreSQL at localhost:5432
```

---

## Phase 4 Acceptance Criteria

```
✓ POST /reviews/local saves review and returns report
✓ POST /reviews/github-pr fetches PR and returns report
✓ GET /reviews/{id} returns saved review with findings
✓ Alembic migration creates all 7 tables cleanly
✓ CLI calls backend when PATCHPROOF_API_URL is set
✓ docker compose up starts the full environment
✓ Integration tests pass for all 3 endpoints
✓ DATABASE_URL and secrets never hardcoded — always from env
```
