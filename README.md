# PatchProof

A spec-to-merge verification tool for AI-generated code changes.

PatchProof analyzes a Git diff or GitHub pull request against the original task description and produces a structured **merge-readiness report** — with a risk score, requirement checklist, missing tests, and a final merge recommendation.

> Not a generic AI code reviewer. Its job is to answer one question:
> **Can we prove this change actually solved the task it claims to solve — safely?**

---

## Quick Start

**Requirements:** Python 3.12+, a Git repo, an OpenAI API key (Phase 2+)

```bash
git clone https://github.com/ethiyor/patchproof.git
cd patchproof
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env   # add your OPENAI_API_KEY
```

---

## Usage

### Review local changes

```bash
# Review all uncommitted changes in the current repo
patchproof review --task task.txt

# Review only staged changes
patchproof review --staged --task task.txt

# Review a saved diff file
patchproof review --diff saved.diff --task task.txt
```

`task.txt` should contain a plain-English description of what the code change was supposed to do.

### Review a GitHub PR (Phase 3+)

```bash
patchproof review-pr https://github.com/org/repo/pull/42 --task task.txt
```

---

## Output

PatchProof writes `patchproof-report.md` to the current directory. Example:

```
## Merge Readiness
Risk score : 7 (High)

## Task Completion Checklist
✅ Added /papers/upload endpoint
❌ No MIME type validation found
❌ No file size limit enforced

## Missing Tests
- [ ] Invalid MIME type rejected (400)
- [ ] File exceeding size limit rejected (413)

## Final Recommendation
Needs changes — 2 security gaps, 3 missing tests.
```

---

## Development Phases

| Phase | Status | What it builds |
|---|---|---|
| 1 — Local CLI | ✅ Done | Git diff → parse → risk score → Markdown report |
| 2 — LLM Pipeline | 🔜 Next | Requirement extraction, per-req verification, test checker |
| 3 — GitHub PR | ⬜ | Fetch PR diff from GitHub URL |
| 4 — Backend + DB | ⬜ | FastAPI + PostgreSQL, review history |
| 5 — GitHub App | ⬜ | Auto-comment on PRs when opened |
| 6 — Dashboard | ⬜ | React web UI, risk trends |

---

## Project Structure

```
cli/          ← CLI entrypoint, git client, GitHub client
core/         ← diff parser, risk scorer, report generator, LLM pipeline
models/       ← Pydantic data models
tests/        ← unit tests, fixtures, golden reports
docs/         ← architecture, API design, phase roadmap
notes/        ← per-milestone build notes
```

---

## Running Tests

```bash
pytest tests/unit/ -v
```

This change is made for the sake fo testing the LLM pipline.