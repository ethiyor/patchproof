# Phase A - Render/Supabase Deployment Preparation

## What changed
- Added Render deployment scripts:
  - `scripts/render_build.sh` for native/manual builds
  - `scripts/render_start.sh` for runtime startup
- Updated `Dockerfile.backend` to a multi-stage production image that builds the React dashboard with Node and runs FastAPI with Python.
- Added `render.yaml` as a Docker-based Render Blueprint/reference configuration.
- Added deployment settings to `backend.config.Settings`:
  - `GITHUB_APP_PRIVATE_KEY`
  - `SERVE_DASHBOARD`
  - `CORS_ORIGINS`
- Updated FastAPI startup to use configurable CORS origins and optional dashboard serving.
- Updated GitHub App JWT creation so the private key can come from either a local file path or a cloud env var.
- Updated `.env.example` with deployment variables.
- Added deployment docs at `docs/deployment/render_supabase.md`.

## Why this matters
Render does not run Docker Compose. This setup gives Render a production Docker image instead. Supabase gives PatchProof a remote Postgres database. These changes make PatchProof ready for that cloud shape without changing the local Docker Compose development flow.

## Critical flow
1. Render builds `Dockerfile.backend`.
2. The Node build stage runs `npm ci` and `npm run build` in `frontend/`.
3. The Python runtime stage installs PatchProof and includes `frontend/dist`.
4. The container starts with `sh scripts/render_start.sh`.
5. The start script runs `alembic upgrade head` against Supabase.
6. Uvicorn starts FastAPI on `0.0.0.0:$PORT`.
7. GitHub can send webhooks to `/github/webhook`.
8. The dashboard is served from `/` when `SERVE_DASHBOARD=true`.

## What this teaches
- Managed Postgres connection strings
- SQLAlchemy driver prefixes such as `postgresql+asyncpg://`
- Cloud build vs runtime commands
- Alembic migration workflow in production
- Platform-provided ports
- Environment variables and secrets
- Webhook URLs without ngrok
