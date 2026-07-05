# 01 — Product Overview

## What PatchProof Is

PatchProof is a **spec-to-merge verification tool** for AI-generated and AI-assisted code changes.

It analyzes a Git diff or GitHub pull request against the original task description and produces a structured **merge-readiness report**.

PatchProof is **not** a generic AI code reviewer. It does not comment on style, suggest refactors, or produce inline suggestions. Its job is to answer one question:

> Can we prove this code change actually solves the task it claims to solve — safely?

---

## The Core Problem

AI coding agents (Cursor, Copilot Agent, Codex, Claude Code, Devin) produce code quickly. But before merging, developers still need to answer:

- Did the AI actually complete the requested task?
- Did it modify unrelated files or introduce scope creep?
- Did it introduce risky changes in auth, database, API, config, security, payments, or file handling?
- Did it add or update meaningful tests?
- Did the frontend/backend API contract remain consistent?
- Which files should a human reviewer inspect before merging?
- Is this safe to merge?

No existing tool focuses squarely on this.

---

## Target Users

| User type | Description |
|---|---|
| **Primary** | Small engineering teams using AI coding agents (Cursor, Copilot, Codex, Devin) |
| **Secondary** | Individual developers who use AI heavily and want to verify local changes before committing |
| **First user (MVP)** | You — run it on Repofy, PaperMind, FurnishUp, and your own PRs |

---

## Why It Is Different From Generic AI PR Review Tools

| Generic AI PR review | PatchProof |
|---|---|
| Asks: "What issues are in this PR?" | Asks: "Did this PR satisfy the original task?" |
| Produces many inline comments | Produces one structured evidence-based report |
| No awareness of the original task/spec | Task description is the primary input |
| Treats every PR the same | Focused specifically on AI-generated changes |
| No merge recommendation with evidence | Gives a final merge decision with cited reasons |
| No test coverage check against task requirements | Checks that tests cover the required scenarios |

The core differentiation in one line:

```
Spec → Diff → Tests → Risk → Evidence → Merge Decision
```

---

## Startup Direction

| Horizon | Description |
|---|---|
| **Short-term** | A CLI and GitHub PR analyzer for AI-generated code changes |
| **Medium-term** | A GitHub App that comments merge-readiness reports on AI-authored PRs |
| **Long-term** | A trust layer for AI-generated software changes across Cursor, Copilot, Codex, Claude Code, Devin, and future coding agents |

The wedge: AI agents increase code output. PatchProof helps teams decide what is safe to merge.
