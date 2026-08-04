import * as vscode from "vscode";

import { reviewLocalChanges } from "../api/patchproofClient";
import { collectWorkingTreeDiff } from "../git/diffCollector";

export class SidebarProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "patchproof.sidebar";

  public constructor(private readonly extensionUri: vscode.Uri) {}

  public resolveWebviewView(webviewView: vscode.WebviewView): void {
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this.extensionUri],
    };

    webviewView.webview.html = this.getHtml();

    webviewView.webview.onDidReceiveMessage(async (message: WebviewMessage) => {
      if (message.type !== "review") {
        return;
      }

      const task = (message.task ?? "").trim();
      if (!task) {
        await webviewView.webview.postMessage({
          type: "error",
          message: "Describe the task before running PatchProof.",
        });
        return;
      }

      try {
        await webviewView.webview.postMessage({ type: "status", message: "Collecting Git diff..." });
        const diff = await collectWorkingTreeDiff();
        await webviewView.webview.postMessage({ type: "status", message: "Sending review to PatchProof..." });

        const report = await reviewLocalChanges({
          task,
          diff,
          repoName: vscode.workspace.name ?? "vscode-workspace",
          branch: "local-changes",
        });

        console.log("PatchProof review completed:", {
          reviewId: report.review_id,
          riskLevel: report.risk_level,
          diffLength: diff.length,
        });

        await webviewView.webview.postMessage({
          type: "report",
          markdown: report.report_markdown,
          summary: `Risk: ${report.risk_level} (${report.risk_score}) � ${report.merge_recommendation}`,
        });
      } catch (error) {
        const messageText = error instanceof Error ? error.message : "Could not run PatchProof review.";
        const friendlyMessage = messageText.includes("fetch failed") || messageText.includes("ECONNREFUSED")
          ? "Could not connect to PatchProof backend. Is it running?"
          : messageText;
        await webviewView.webview.postMessage({
          type: "error",
          message: friendlyMessage,
        });
      }
    });
  }

  private getHtml(): string {
    const nonce = getNonce();

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PatchProof</title>
  <style>
    body {
      color: var(--vscode-foreground);
      background: var(--vscode-sideBar-background);
      font-family: var(--vscode-font-family);
      font-size: var(--vscode-font-size);
      margin: 0;
      padding: 16px;
    }

    h1 {
      font-size: 16px;
      font-weight: 600;
      margin: 0 0 8px;
    }

    p {
      color: var(--vscode-descriptionForeground);
      line-height: 1.45;
      margin: 0;
    }

    label {
      display: block;
      font-weight: 600;
      margin: 18px 0 8px;
    }

    textarea {
      box-sizing: border-box;
      width: 100%;
      min-height: 128px;
      resize: vertical;
      color: var(--vscode-input-foreground);
      background: var(--vscode-input-background);
      border: 1px solid var(--vscode-input-border);
      border-radius: 2px;
      font-family: var(--vscode-font-family);
      font-size: var(--vscode-font-size);
      line-height: 1.4;
      padding: 8px;
    }

    textarea:focus {
      outline: 1px solid var(--vscode-focusBorder);
      outline-offset: -1px;
    }

    button {
      width: 100%;
      color: var(--vscode-button-foreground);
      background: var(--vscode-button-background);
      border: 0;
      border-radius: 2px;
      cursor: pointer;
      font: inherit;
      margin-top: 12px;
      padding: 8px 10px;
    }

    button:hover {
      background: var(--vscode-button-hoverBackground);
    }

    button:disabled {
      cursor: wait;
      opacity: 0.7;
    }

    #result {
      border-top: 1px solid var(--vscode-sideBarSectionHeader-border);
      margin-top: 16px;
      min-height: 20px;
      padding-top: 12px;
    }

    .status {
      color: var(--vscode-descriptionForeground);
      white-space: pre-wrap;
    }

    .error {
      color: var(--vscode-errorForeground);
      white-space: pre-wrap;
    }

    .summary {
      color: var(--vscode-descriptionForeground);
      margin-bottom: 12px;
    }

    .report h1,
    .report h2,
    .report h3 {
      font-size: 14px;
      margin: 16px 0 8px;
    }

    .report p,
    .report li {
      color: var(--vscode-foreground);
      line-height: 1.45;
    }

    .report code {
      background: var(--vscode-textCodeBlock-background);
      border-radius: 2px;
      font-family: var(--vscode-editor-font-family);
      padding: 1px 3px;
    }

    .report pre {
      background: var(--vscode-textCodeBlock-background);
      overflow-x: auto;
      padding: 8px;
    }
  </style>
</head>
<body>
  <h1>PatchProof</h1>
  <p>Describe the change you intended to make, then run a local review.</p>

  <label for="task">Describe your task</label>
  <textarea id="task" placeholder="Example: Add AWS deployment docs and a dashboard detail view."></textarea>
  <button id="review" type="button">Run PatchProof</button>
  <div id="result" role="status" aria-live="polite"></div>

  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    const taskInput = document.getElementById("task");
    const reviewButton = document.getElementById("review");
    const result = document.getElementById("result");

    reviewButton.addEventListener("click", () => {
      const task = taskInput.value.trim();
      setLoading(Boolean(task));
      renderStatus(task ? "Collecting Git diff..." : "Describe your task before running PatchProof.");
      vscode.postMessage({ type: "review", task });
    });

    window.addEventListener("message", (event) => {
      const message = event.data;
      if (message.type === "status") {
        renderStatus(message.message);
      }
      if (message.type === "error") {
        setLoading(false);
        renderError(message.message);
      }
      if (message.type === "report") {
        setLoading(false);
        renderReport(message.markdown, message.summary);
      }
    });

    function setLoading(isLoading) {
      reviewButton.disabled = isLoading;
      reviewButton.textContent = isLoading ? "Running PatchProof..." : "Run PatchProof";
    }

    function renderStatus(message) {
      result.innerHTML = '<div class="status">' + escapeHtml(message) + '</div>';
    }

    function renderError(message) {
      result.innerHTML = '<div class="error">' + escapeHtml(message) + '</div>';
    }

    function renderReport(markdown, summary) {
      result.innerHTML = '<div class="summary">' + escapeHtml(summary) + '</div><div class="report">' + renderMarkdown(markdown) + '</div>';
    }

    function renderMarkdown(markdown) {
      const escaped = escapeHtml(markdown);
      return escaped
        .replace(/^### (.*)$/gm, "<h3>$1</h3>")
        .replace(/^## (.*)$/gm, "<h2>$1</h2>")
        .replace(/^# (.*)$/gm, "<h1>$1</h1>")
        .replace(/\`([^\`]+)\`/g, "<code>$1</code>")
        .replace(/^[-*] (.*)$/gm, "<li>$1</li>")
        .replace(/\n{2,}/g, "</p><p>")
        .replace(/\n/g, "<br>")
        .replace(/^/, "<p>")
        .replace(/$/, "</p>");
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }
  </script>
</body>
</html>`;
  }
}

type WebviewMessage = {
  type: string;
  task?: string;
};

function getNonce(): string {
  const possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let text = "";
  for (let index = 0; index < 32; index += 1) {
    text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return text;
}


