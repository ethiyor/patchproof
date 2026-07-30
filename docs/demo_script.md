# PatchProof Demo Script

Use this for a 3-5 minute screen recording.

## 1. Open the Pull Request

Show a real PR with a small but meaningful change. Say:

```text
PatchProof checks whether a code change actually satisfies the task it claims to solve, then reports risk, missing tests, and merge readiness.
```

## 2. Show the Trigge

Open the GitHub App settings or PR timeline and show that a pull request event is sent to PatchProof through the webhook URL.

## 3. Show the PR Comment

Walk through the PatchProof comment:

- Merge recommendation.
- Risk score and risk level.
- Requirement checklist.
- Evidence from changed files.
- Missing tests or risky areas.

## 4. Show the Dashboard

Open the dashboard and show:

- Review list.
- Risk filter.
- Review detail page.
- Risk trend chart.

## 5. Show the VS Code Extension

Open the PatchProof sidebar in VS Code:

- Type a task.
- Run the review against local Git changes.
- Show the returned report inside the sidebar.

## 6. End With Architecture

Say:

```text
The system has a CLI, GitHub App automation, FastAPI backend, PostgreSQL persistence, React dashboard, and VS Code extension. The deployed version runs on AWS with ECR, ECS Fargate, an Application Load Balancer, and RDS PostgreSQL.
```
