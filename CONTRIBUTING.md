# Contributing to PatchProof

Thanks for your interest in PatchProof. This project is still early, so the best contributions are focused, well-tested improvements to the CLI, review engine, backend API, dashboard, VS Code extension, documentation, or test coverage.

## Development Setup

```bash
git clone https://github.com/ethiyor/patchproof.git
cd patchproof
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
```

For the backend and local database:

```bash
docker compose up
```

For the dashboard:

```bash
cd frontend
npm install
npm run dev
```

For the VS Code extension:

```bash
cd vscode-extension
npm install
npm run compile
```

## Before Opening a Pull Request

Run the relevant checks:

```bash
.venv/bin/python -m pytest tests/unit -q
.venv/bin/python -m pytest tests/integration -q
```

If you changed the VS Code extension:

```bash
cd vscode-extension
npm run compile
```

If you changed database schema:

- Update SQLAlchemy models.
- Add a new Alembic migration.
- Do not edit an already-applied migration unless the project maintainers explicitly ask you to.

## Code Style

- Keep changes small and focused.
- Prefer existing project patterns over new abstractions.
- Add tests for behavior changes.
- Use typed Pydantic models for structured review data.
- Avoid real network calls in unit tests; mock OpenAI and GitHub calls.
- Do not commit generated reports, local database files, virtual environments, node modules, or packaged `.vsix` files.

## Security Rules

Do not commit secrets. This includes:

- `.env` files
- OpenAI API keys
- GitHub personal access tokens
- GitHub App private keys
- AWS credentials
- database passwords
- production URLs that include credentials

Use `.env.example` for placeholder names only. If you accidentally commit a secret, rotate it immediately and tell maintainers so history can be cleaned before release.

## Pull Request Checklist

- [ ] The change has a clear purpose.
- [ ] Tests were added or updated where appropriate.
- [ ] Unit tests pass.
- [ ] Integration tests pass if backend behavior changed.
- [ ] VS Code extension compile passes if extension code changed.
- [ ] No secrets or generated artifacts are committed.
- [ ] Documentation was updated if user-facing behavior changed.
