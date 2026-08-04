# PatchProof

PatchProof is an AI-powered merge-readiness tool for code changes. It compares a Git diff or GitHub pull request against the original task, checks whether the requested behavior was implemented, flags missing tests and risky files, and produces an evidence-based review report.

PatchProof is built as a developer tool with multiple surfaces:

- CLI for local and GitHub PR reviews.
- FastAPI backend with PostgreSQL persistence.
- GitHub App webhook automation for pull request analysis and comments.
- React/TypeScript dashboard for review history and risk trends.
- VS Code extension for local diff reviews from the editor.

## Why PatchProof

AI coding tools can generate large patches quickly, but reviewers still need to answer the same hard question: did this change actually satisfy the task, and is it safe to merge? PatchProof focuses on task alignment, evidence, missing tests, and merge-readiness instead of generic style comments.

## Architecture

```text
CLI / GitHub App / VS Code Extension / Dashboard
        |
        v
FastAPI backend
        |
        v
Review engine
(diff parsing, task checks, test checks, risk scoring, report generation)
        |
        v
PostgreSQL review history
        |
        v
Markdown report, dashboard view, or GitHub PR comment
```

Deployment work has also been tested with AWS components:

```text
GitHub webhook -> Application Load Balancer -> ECS Fargate -> FastAPI -> RDS PostgreSQL
```

## Features

- Parse Git diffs into structured file, hunk, addition, deletion, and risk metadata.
- Analyze implementation against a natural-language task description.
- Detect risky paths such as auth, migrations, configuration, and security-sensitive files.
- Identify missing or weak test coverage signals.
- Generate Markdown merge-readiness reports.
- Store reviews, findings, requirement checks, changed files, repositories, and pull requests in PostgreSQL.
- Verify GitHub webhook signatures and authenticate as a GitHub App with installation tokens.
- Post PatchProof reports back to pull requests.
- Reuse the original PR task context when new commits are pushed to an existing PR.
- Run local reviews from a packaged VS Code extension.

## Prerequisites

- Python 3.12+
- Node.js 20+ for the dashboard or VS Code extension
- Docker Desktop for local backend/database development
- OpenAI API key for real LLM-backed reviews
- Optional: GitHub token for CLI PR review
- Optional: GitHub App credentials for webhook automation

## Quick Start: CLI

```bash
git clone https://github.com/ethiyor/patchproof.git
cd patchproof
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Add your required environment values to `.env`, then run:

```bash
patchproof review --task task.txt
```

Other useful CLI commands:

```bash
patchproof review --staged --task task.txt
patchproof review --diff saved.diff --task task.txt
patchproof review-pr https://github.com/org/repo/pull/42 --task task.txt
```

## Local Backend and Database

Run the local FastAPI backend and PostgreSQL database with Docker Compose:

```bash
docker compose up
```

Local URLs:

- Backend API: `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`

The backend waits for Postgres, runs `alembic upgrade head`, then starts Uvicorn.

Stop the stack:

```bash
docker compose down
```

Delete local Postgres data too:

```bash
docker compose down -v
```

## Backend API

Common endpoints:

```text
GET  /health
POST /reviews/local
POST /reviews/github-pr
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

## GitHub App Webhooks

For GitHub App automation, set the webhook URL to your backend URL plus `/github/webhook`:

```text
https://your-backend.example.com/github/webhook
```

For local development, expose the backend with a tunnel such as ngrok:

```text
https://your-ngrok-domain.ngrok-free.dev/github/webhook
```

PatchProof validates `X-Hub-Signature-256`, processes `pull_request` events, fetches PR metadata/diff with a GitHub App installation token, stores the review, and posts a PR comment.

## Dashboard

```bash
cd frontend
npm install
npm run dev
```

The dashboard reads review history from the backend and provides review list/detail views, filters, and risk trend visualization.

## VS Code Extension

```bash
cd vscode-extension
npm install
npm run compile
npm run package
```

The extension collects the active repository's Git diff, sends it to the configured PatchProof backend, and renders the returned report in the sidebar.

Configure the backend URL in VS Code settings:

```json
{
  "patchproof.apiUrl": "http://localhost:8000"
}
```

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

Current local verification snapshot: 364 Python tests pass, plus the TypeScript extension build.

## Project Structure

```text
backend/            FastAPI routes, database models, migrations, GitHub App services
cli/                CLI commands, local review flow, GitHub PR review flow
core/               Diff parser, risk scorer, task/test verification, reports
frontend/           React/TypeScript dashboard
llm/                LLM client abstractions
models/             Pydantic models shared by the review pipeline
tests/              Unit tests, integration tests, fixtures, golden reports
vscode-extension/   PatchProof VS Code sidebar extension
docs/               Architecture, API, deployment, and phase docs
notes/              Per-milestone implementation notes
```

## Security Notes

- Never commit `.env`, private keys, tokens, or cloud credentials.
- Rotate any credential that was ever committed before making a repo public.
- Use separate credentials for local development and deployed environments.
- Prefer cloud secret stores for hosted deployments.

## Limitations

PatchProof is an assistive review tool, not a replacement for human review. LLM-backed findings can be incomplete or wrong, so reports should be treated as structured review evidence rather than final authority.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

PatchProof is released under the [MIT License](LICENSE).
