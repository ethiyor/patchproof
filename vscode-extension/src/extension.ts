import * as vscode from "vscode";

import { SidebarProvider } from "./sidebar/SidebarProvider";

export function activate(context: vscode.ExtensionContext): void {
  const sidebarProvider = new SidebarProvider(context.extensionUri);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(SidebarProvider.viewType, sidebarProvider),
    vscode.commands.registerCommand("patchproof.reviewLocalChanges", async () => {
      await vscode.window.showInformationMessage("PatchProof ready");
    }),
  );
}

export function deactivate(): void {
  // No background resources to dispose yet.
}
