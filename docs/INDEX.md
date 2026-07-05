# PatchProof — Documentation Index

Use this file to navigate the project docs. Each file covers one topic.
When asking Copilot to implement something, reference the specific phase milestone file.

---

## Reference Docs

| File | Contents |
|---|---|
| [01_product_overview.md](01_product_overview.md) | What PatchProof is, core problem, target users, differentiation |
| [02_mvp_definition.md](02_mvp_definition.md) | MVP scope, explicit exclusions, success criteria |
| [03_user_workflows.md](03_user_workflows.md) | Step-by-step flows: Local CLI, GitHub PR, GitHub App, VS Code |
| [04_architecture.md](04_architecture.md) | Architecture diagram, data flow, tech stack, core modules |
| [05_data_models_and_api.md](05_data_models_and_api.md) | Database tables + FastAPI endpoint contracts |
| [06_llm_pipeline.md](06_llm_pipeline.md) | 5-step LLM pipeline with inputs, outputs, failure cases |
| [07_risk_scoring_and_report.md](07_risk_scoring_and_report.md) | Risk scoring rules + full Markdown report format |
| [08_testing_and_security.md](08_testing_and_security.md) | Testing strategy, sample fixtures, security requirements |
| [09_resume_and_next_steps.md](09_resume_and_next_steps.md) | Resume bullets per version + next 7-day checklist |

---

## Implementation Phases

Each phase file is broken into numbered milestones.
**Implement one milestone at a time.** When you are ready to start a milestone, say:
> "Implement Phase N, Milestone N.M"

| Phase | File | What gets built |
|---|---|---|
| 1 | [phases/phase_01_local_cli.md](phases/phase_01_local_cli.md) | Python CLI, git diff collection, diff parser, risk scorer, report writer |
| 2 | [phases/phase_02_llm_pipeline.md](phases/phase_02_llm_pipeline.md) | OpenAI integration, requirement extraction, per-req verification, test checker |
| 3 | [phases/phase_03_github_pr.md](phases/phase_03_github_pr.md) | GitHub REST API client, PR diff fetching, `review-pr` command |
| 4 | [phases/phase_04_backend_db.md](phases/phase_04_backend_db.md) | FastAPI backend, PostgreSQL, SQLAlchemy, Alembic, Docker Compose |
| 5 | [phases/phase_05_github_app.md](phases/phase_05_github_app.md) | GitHub App, webhook handling, JWT auth, auto PR comments |
| 6 | [phases/phase_06_dashboard.md](phases/phase_06_dashboard.md) | React + Tailwind dashboard, review history, risk charts |
| 7 | [phases/phase_07_vscode_extension.md](phases/phase_07_vscode_extension.md) | VS Code extension, sidebar panel, inline report display |
| 8 | [phases/phase_08_polish.md](phases/phase_08_polish.md) | Tests, deployment, README, demo video |

---

## How to Use These Docs

1. Read [01_product_overview.md](01_product_overview.md) and [02_mvp_definition.md](02_mvp_definition.md) to understand what you are building.
2. Start with [phases/phase_01_local_cli.md](phases/phase_01_local_cli.md), Milestone 1.1.
3. When implementing a milestone, also reference [04_architecture.md](04_architecture.md) for module responsibilities and [06_llm_pipeline.md](06_llm_pipeline.md) for LLM steps.
4. Use [05_data_models_and_api.md](05_data_models_and_api.md) as the source of truth for database schema and API contracts.
5. Check [08_testing_and_security.md](08_testing_and_security.md) before shipping each phase.
