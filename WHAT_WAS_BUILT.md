# What Was Built - PatchProof

This file summarizes the current state of PatchProof. Detailed milestone notes are archived in `notes/`.

## Current State

PatchProof has grown from a local CLI into a full code-review platform:

- Local CLI review of working-tree, staged, saved diff, and GitHub PR changes.
- Modular review engine for diff parsing, task analysis, requirement checks, missing-test detection, risk scoring, and Markdown report generation.
- FastAPI backend with PostgreSQL persistence and Alembic migrations.
- GitHub App webhook flow with signature verification, installation-token auth, PR analysis, and PR comment posting.
- React dashboard for review history, detail pages, filtering, and risk trends.
- VS Code extension sidebar that collects the current Git diff and sends it to the backend.
- Local Docker Compose stack and AWS deployment path using ECR, ECS Fargate, ALB, and RDS PostgreSQL.

## Latest Milestones

| Phase | Status | What it added |
|---|---|---|
| 4 | Complete | Backend, PostgreSQL models, migrations, local/GitHub review endpoints, Docker Compose |
| 5 | Complete | GitHub App registration, webhook verification, JWT installation-token auth, background PR analysis, PR comments, end-to-end test flow |
| 6 | Complete | React/Vite dashboard, review list, detail view, filters, risk trend chart, production build |
| 7 | Complete | VS Code extension scaffold, task input sidebar, Git diff collection, backend API call, report rendering |
| 8 | Repo polish in progress | Test verification, README refresh, deployment notes, demo script preparation |

## How PatchProof Works

```text
1. A developer gives PatchProof a task and a diff, or GitHub sends a pull request webhook.
2. PatchProof parses the changed files and hunks.
3. The review engine checks task alignment, risk-sensitive paths, missing tests, and evidence.
4. The backend stores the report, findings, requirement checks, and changed files in PostgreSQL.
5. The result is returned to the caller, shown in the dashboard/extension, or posted back to the PR.
```

## Validation Snapshot

Latest local verification:

```bash
.venv/bin/python -m pytest tests/unit -q
# 356 passed, 1 warning

.venv/bin/python -m pytest tests/integration -q
# 5 passed

cd vscode-extension && npm run compile
# TypeScript compile succeeded
```

## Remaining Manual Polish

- Record and upload the 3-5 minute demo video.
- Add the demo video link and screenshots/GIFs to the README.
- Move deployed ECS secrets from plaintext task-definition values into AWS Secrets Manager.
- Add HTTPS to the AWS load balancer before treating the deployment as production-like.
