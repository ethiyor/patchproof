# Phase 7 — VS Code / Cursor Extension

**Prerequisites:** Phase 4 complete. Backend is running and accessible.
**Reference docs:** [03_user_workflows.md](../03_user_workflows.md)

---

## Overview

Build a VS Code extension with a sidebar panel. The developer types a task description, clicks "Review", and sees the PatchProof report inline — without leaving the editor.

---

## Milestone 7.1 — Extension Scaffold

**Goal:** A runnable VS Code extension with a sidebar view.

**Files to create:**

```
vscode-extension/package.json
vscode-extension/src/extension.ts
vscode-extension/src/sidebar/SidebarProvider.ts
vscode-extension/.vscodeignore
vscode-extension/tsconfig.json
```

**Tasks:**
- `yo code` → generate a new extension with TypeScript and a Webview sidebar
- Set `activationEvents: ["onStartupFinished"]`
- Register a `TreeView` or `WebviewView` for the PatchProof sidebar panel
- Verify: extension loads in VS Code Extension Development Host with no errors
- Add `patchproof.reviewLocalChanges` command that shows a notification: "PatchProof ready"

**Done when:**
- Extension loads in Extension Development Host
- PatchProof icon appears in the Activity Bar
- Command `patchproof.reviewLocalChanges` runs without errors

---

## Milestone 7.2 — Sidebar Panel + Task Input

**Goal:** A sidebar Webview with a task text area and a "Review" button.

**Files to create:**

```
vscode-extension/src/sidebar/SidebarProvider.ts
vscode-extension/src/sidebar/webview.html
```

**Tasks:**
- Implement `WebviewView` that renders an HTML form:
  - Text area: "Describe your task"
  - Button: "Run PatchProof"
  - Result area (initially empty)
- Use VS Code Webview API — no external JS frameworks needed at this stage
- Handle message passing: Webview → Extension Host → back to Webview
- On button click, post a `{type: "review", task: "..."}` message to the extension host

**Done when:**
- Sidebar renders with text area and button
- Clicking "Run PatchProof" logs the task text to the extension console

---

## Milestone 7.3 — Git Diff Collection via VS Code API

**Goal:** Collect the current working tree diff using VS Code's built-in Git extension.

**Files to create:**

```
vscode-extension/src/git/diffCollector.ts
```

**Tasks:**
- Access VS Code Git API: `vscode.extensions.getExtension("vscode.git").exports.getAPI(1)`
- Get the active repository
- Collect working tree changes: `repo.diff()` or `repo.state.workingTreeChanges`
- Generate unified diff text from changed files
- Handle: no git repo open, no changes, binary files
- Return diff text to the sidebar handler

**Done when:**
- Given uncommitted changes in the workspace, `diffCollector.ts` returns a non-empty unified diff string

---

## Milestone 7.4 — Backend Call + Report Display

**Goal:** Send the diff + task to the PatchProof backend and display the report in the sidebar.

**Files to modify:**

```
vscode-extension/src/sidebar/SidebarProvider.ts
vscode-extension/src/api/patchproofClient.ts  (new)
```

**Tasks:**
- Read `PATCHPROOF_API_URL` from VS Code settings (default: `http://localhost:8000`)
- Create `patchproofClient.ts` — calls `POST /reviews/local` with diff + task using `node-fetch` or `axios`
- On success: post `{type: "report", markdown: "..."}` back to the Webview
- In Webview: render the returned Markdown using a simple marked.js renderer
- Show loading state while request is in flight
- Show error state if backend is unreachable

**Done when:**
- With backend running: clicking "Run PatchProof" displays the report in the sidebar
- Without backend: shows "Could not connect to PatchProof backend. Is it running?"

---

## Phase 7 Acceptance Criteria

```
✓ Extension loads without errors in VS Code Extension Development Host
✓ Sidebar panel shows task input and Review button
✓ Git diff collected from VS Code Git API
✓ Report displayed in sidebar after backend call
✓ Loading and error states handled
✓ PATCHPROOF_API_URL configurable via VS Code settings
```
