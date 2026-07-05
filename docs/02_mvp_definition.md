# 02 — MVP Definition

## What the MVP Is

The MVP is a **local Python CLI** that:

1. Reads a Git diff from the current working tree (or a saved `.diff` file)
2. Reads a task description from a `task.txt` file
3. Runs a 5-step LLM pipeline to verify requirements, summarize the diff, assess risk, and check tests
4. Writes a `patchproof-report.md` file with a structured, evidence-based report

No server. No database. No GitHub App. Just a CLI tool that takes a diff and a task and tells you if it is safe to merge.

---

## What Is Excluded From the MVP

```
✗ No database — reports are written to disk only
✗ No FastAPI backend server
✗ No GitHub App or webhook handling
✗ No frontend dashboard
✗ No multi-user support or authentication
✗ No VS Code / Cursor extension
✗ No AST parsing or embeddings
✗ No CI/CD integration
✗ No Rust — Python only
```

These are all built in later phases. The MVP proves the core idea works.

---

## MVP Commands

```bash
# Review current working tree diff against a task
patchproof review --task task.txt

# Review only staged changes
patchproof review --staged --task task.txt

# Review a saved diff file
patchproof review --diff saved.diff --task task.txt
```

---

## MVP Output

A file named `patchproof-report.md` written to the current directory.

---

## MVP Success Criteria

The MVP is successful when running it on a real diff produces a report that contains:

```
✓ 5 clear task requirements identified from task.txt
✓ Status for each requirement: satisfied / partially_satisfied / missing / unclear
✓ Risk score with specific, evidence-backed reasons
✓ Missing test checklist with expected test cases
✓ 2–5 findings, each citing a file path and a concrete reason
✓ Final merge recommendation: Ready / Ready with comments / Needs changes / Do not merge
```

**Measure success by:**
- Can it save a developer 10–15 minutes of review time?
- Can it catch a missing test that a human would miss?
- Can it identify a risky AI-generated change?
- Can it tell you which specific file to inspect first?

---

## MVP Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| CLI | Typer |
| Git | GitPython |
| HTTP (OpenAI) | httpx |
| Validation | Pydantic v2 |
| LLM | OpenAI API (GPT-4o) |
| Config | python-dotenv |
| Output | Markdown file |
