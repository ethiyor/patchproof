# PatchProof

PatchProof is an AI-powered merge-readiness system for code changes. It compares a Git diff or GitHub pull request against the original task, checks whether the requested behavior was actually implemented, flags missing tests and risky files, and produces an evidence-based review report.

PatchProof now has four entry points:

- CLI for local and PR-based reviews.
- FastAPI backend with PostgreSQL persistence.
- GitHub App webhook flow that can comment on pull requests.
- React dashboard and VS Code extension surfaces for reviewing history and local changes.

## Architecture

```text
Developer / GitHub PR / VS Code
        |
        v
PatchProof CLI, GitHub App webhook, or VS Code extension
        |
        v
FastAPI backend
        |
        v
Review engine: diff parsing, requirement verification, test checks, risk scoring, report generation
        |
        v
PostgreSQL review history + GitHub PR comment when triggered by webhook
```

For the AWS deployment you built during development, the deployed path is:

```text
GitHub webhook -> Application Load Balancer -> ECS Fargate task -> FastAPI -> Amazon RDS PostgreSQL
```

## Prerequisites

- Python 3.12+
- Node.js 20+
- Docker Desktop, if you want the local backend/database stack
- PostgreSQL client tools, if you want to inspect a remote database with `psql`
- OpenAI API key for real LLM-backed reviews
- GitHub App credentials for webhook and PR comment automation

## Environment

Create your local `.env` from the example file:

```bash
cp .env.example .env
```

Common local values:

```bash
OPENAI_API_KEY=...
DATABASE_URL=postgresql+asyncpg://patchproof:patchproof@localhost:5432/patchproof
GITHUB_WEBHOOK_SECRET=...
GITHUB_APP_ID=...
GITHUB_APP_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n
# Optional for CLI-only GitHub requests
GITHUB_TOKEN=...
```

Do not commit `.env`, private keys, GitHub tokens, or OpenAI keys.

## Quick Start: CLI

```bash
git clone https://github.com/ethiyor/patchproof.git
cd patchproof
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Review local changes:

```bash
patchproof review --task task.txt
```

Review staged changes only:

```bash
patchproof review --staged --task task.txt
```

Review a saved diff file:

```bash
patchproof review --diff saved.diff --task task.txt
```

Review a GitHub pull request:

```bash
patchproof review-pr https://github.com/org/repo/pull/42 --task task.txt
```

## Quick Start: Backend and Database

Run the local FastAPI backend and PostgreSQL database with Docker Compose:

```bash
docker compose up
```

Local URLs:

- Backend API: `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`

The Compose backend waits for Postgres, runs `alembic upgrade head`, then starts Uvicorn with reload enabled.

To stop containers:

```bash
docker compose down
```

To stop containers and delete local Postgres data:

```bash
docker compose down -v
```

## Backend API

Useful endpoints:

```text
GET  /health
POST /reviews/local
POST /reviews/github-p
GET  /reviews/{review_id}
GET  /reviews?page=1&limit=20&risk_level=high
POST /github/webhook
```

Example local review request:

```bash
curl -X POST http://localhost:8000/reviews/local \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Add a hello endpoint",
    "diff": "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@ -0,0 +1 @@\n+print(\"hello\")",
    "repo_name": "patchproof",
    "branch": "demo",
    "changed_files": ["app.py"]
  }'
```

## GitHub App Webhook

In GitHub App settings, set the webhook URL to your backend URL plus `/github/webhook`:

```text
https://your-backend-domain.example.com/github/webhook
```

For local development with ngrok:

```text
https://your-ngrok-domain.ngrok-free.dev/github/webhook
```

For the AWS ECS deployment, use the ALB DNS name once `/health` works through the load balancer:

```text
http://your-alb-dns-name.us-east-2.elb.amazonaws.com/github/webhook
```

The webhook endpoint verifies GitHub's signature, receives pull request events, fetches PR context through the GitHub App installation token, runs PatchProof, stores the result, and posts a PR comment.

## React Dashboard

```bash
cd frontend
npm install
npm run dev
```

The dashboard reads review history from the backend and provides list/detail views, filters, and risk trend visualization.

If the backend is not on `http://localhost:8000`, configure the frontend API base URL through the Vite environment file used by the frontend.

## VS Code Extension

```bash
cd vscode-extension
npm install
npm run compile
```

To run it locally:

1. Open the repo in VS Code.
2. Open `vscode-extension/src/extension.ts`.
3. Press `F5` to launch an Extension Development Host.
4. Open the PatchProof activity bar view.
5. Enter a task description and run the review.

The extension reads your current Git diff, sends it to the configured backend, and renders the returned PatchProof report in the sidebar.

Configure the backend URL in VS Code settings:

```json
{
  "patchproof.apiUrl": "http://localhost:8000"
}
```

## AWS Deployment Notes

The current AWS learning deployment uses:

- Amazon ECR for the Docker image.
- ECS Fargate for running the FastAPI container.
- Application Load Balancer for public HTTP access.
- Amazon RDS PostgreSQL for persistent review data.
- IAM roles for ECS image pull, logging, and secret access.
- Security groups to control HTTP and PostgreSQL traffic.

Recommended production hardening still to do:

- Move all task-definition plaintext secrets into AWS Secrets Manager.
- Use HTTPS on the load balancer with ACM.
- Restrict RDS access to ECS security groups instead of personal IPs.
- Add CloudWatch alarms and log retention.
- Build CI/CD so pushing a release image updates the ECS service automatically.

## Tests

Run unit tests:

```bash
.venv/bin/python -m pytest tests/unit -q
```

Run integration tests:

```bash
.venv/bin/python -m pytest tests/integration -q
```

Compile the VS Code extension:

```bash
cd vscode-extension
npm run compile
```

## Project Structure

```text
backend/            FastAPI app, API routes, database models, migrations
cli/                CLI commands, local review flow, GitHub PR commands
core/               Diff parser, LLM pipeline, verification, scoring, reports
frontend/           React dashboard
llm/                LLM client abstractions and prompt-facing helpers
models/             Pydantic models shared by review pipeline code
tests/              Unit tests, integration tests, fixtures, golden reports
vscode-extension/   PatchProof VS Code sidebar extension
notes/              Per-milestone implementation notes
docs/               Phase roadmap, architecture, API, and security docs
```

## Contributing

Keep changes focused, add or update tests for behavior changes, and avoid committing generated artifacts or secrets. For database schema changes, update SQLAlchemy models and create an Alembic migration rather than editing an already-applied migration.
