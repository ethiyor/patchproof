# Render + Supabase Deployment Guide

This guide deploys PatchProof as one Docker-based Render Web Service:

- FastAPI backend serves API routes and GitHub webhooks.
- The React dashboard is built into `frontend/dist` and served by FastAPI.
- Supabase provides the managed PostgreSQL database.
- Alembic runs during service startup so the remote schema is upgraded before the app accepts traffic.

## 1. Create the Supabase database

1. Create a Supabase project named `patchproof-staging`.
2. Pick the same region family you plan to use in Render when possible.
3. Save the database password you chose during project creation. Supabase will need it when generating the connection string.

## 2. Get the Supabase database connection string

From the Supabase screen shown in your screenshot:

1. Stay inside the PatchProof Supabase project.
2. In the left sidebar, click **Connect** near the top of the project page.
3. Choose **Connection string**.
4. Select the **Session pooler** or **Transaction pooler** connection string, not the raw local-only examples.
5. Copy the URI-style connection string.
6. Replace `[YOUR-PASSWORD]` with your real Supabase database password.
7. Convert the prefix for PatchProof's SQLAlchemy async driver.

Supabase usually gives something shaped like this:

```text
postgresql://postgres.PROJECT_REF:[YOUR-PASSWORD]@aws-0-us-west-2.pooler.supabase.com:5432/postgres
```

PatchProof needs the SQLAlchemy asyncpg driver prefix:

```text
postgresql+asyncpg://postgres.PROJECT_REF:YOUR_REAL_PASSWORD@aws-0-us-west-2.pooler.supabase.com:5432/postgres
```

If Supabase gives `postgres://...`, convert it the same way:

```text
postgres://...
```

becomes:

```text
postgresql+asyncpg://...
```

Use that final value as Render's `DATABASE_URL` environment variable.

Render often connects from IPv4 infrastructure, so the Supabase pooler is the safest first choice. Direct database connections can be fine later, but the pooler is usually smoother for a first deployment.

## 3. Prepare Render service

Create a new Render Web Service from the GitHub repository.

Use Docker deployment:

```text
Dockerfile path: ./Dockerfile.backend
Docker context: .
```

The Dockerfile uses a multi-stage build:

1. A Node stage installs frontend dependencies and builds `frontend/dist`.
2. A Python stage installs PatchProof and copies the built dashboard into the runtime image.
3. The container starts with `sh scripts/render_start.sh`.

The start script runs:

```bash
alembic upgrade head
uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
```

`0.0.0.0` lets Render's load balancer reach the service. `$PORT` is the port Render assigns at runtime.

The included `render.yaml` records this setup as a Render Blueprint/reference config.

## 4. Render environment variables

Set these in Render:

```text
DATABASE_URL=postgresql+asyncpg://postgres.PROJECT_REF:YOUR_REAL_PASSWORD@aws-0-us-west-2.pooler.supabase.com:5432/postgres
OPENAI_API_KEY=...
GITHUB_APP_ID=...
GITHUB_APP_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----
GITHUB_WEBHOOK_SECRET=...
SECRET_KEY=<long random string>
DEBUG=false
SERVE_DASHBOARD=true
CORS_ORIGINS=https://YOUR-RENDER-SERVICE.onrender.com,http://localhost:5173
```

Do not commit the real `DATABASE_URL` or password to Git. It belongs only in Render's environment variables.

You can use `GITHUB_APP_PRIVATE_KEY_PATH` instead of `GITHUB_APP_PRIVATE_KEY` if you configure a Render secret file. For the fastest first deploy, `GITHUB_APP_PRIVATE_KEY` with escaped `\n` line breaks is simpler.

## 5. First deploy checks

After Render deploys, check logs for this order:

```text
Docker frontend build stage succeeded
alembic upgrade head succeeded
container started uvicorn
```

Then open:

```text
https://YOUR-RENDER-SERVICE.onrender.com/health
```

Expected:

```json
{"status":"ok"}
```

Then open:

```text
https://YOUR-RENDER-SERVICE.onrender.com/
```

You should see the dashboard if `SERVE_DASHBOARD=true` and the Docker frontend build stage succeeded.

## 6. Confirm migrations in Supabase

In Supabase SQL Editor:

```sql
select * from alembic_version;
```

```sql
select table_name
from information_schema.tables
where table_schema = 'public'
order by table_name;
```

This confirms Render ran Alembic against the remote Supabase database.

## 7. Move GitHub webhook

In GitHub App settings, change the webhook URL to:

```text
https://YOUR-RENDER-SERVICE.onrender.com/github/webhook
```

Make sure the GitHub App webhook secret matches `GITHUB_WEBHOOK_SECRET` in Render.

## 8. Security warning

The dashboard is still global to the database. Until GitHub OAuth and user-specific scoping exist, do not treat the public dashboard URL as safe for real private teams.

For a safer temporary deployment, set:

```text
SERVE_DASHBOARD=false
```

That leaves `/health` and `/github/webhook` available while hiding the dashboard.
