import * as vscode from "vscode";

type GitExtension = vscode.Extension<{
  getAPI(version: 1): GitAPI;
}>;

type GitAPI = {
  repositories: Repository[];
};

type Repository = {
  rootUri: vscode.Uri;
  diff(): Promise<string>;
};

export async function collectWorkingTreeDiff(): Promise<string> {
  const gitExtension = vscode.extensions.getExtension("vscode.git") as GitExtension | undefined;
  if (!gitExtension) {
    throw new Error("VS Code Git extension is unavailable.");
  }

  const gitApi = gitExtension.isActive ? gitExtension.exports.getAPI(1) : (await gitExtension.activate()).getAPI(1);
  const repository = getActiveRepository(gitApi.repositories);
  if (!repository) {
    throw new Error("Open a Git repository before running PatchProof.");
  }

  const diff = await repository.diff();
  if (!diff.trim()) {
    throw new Error("No local Git changes found to review.");
  }

  return diff;
}

function getActiveRepository(repositories: Repository[]): Repository | undefined {
  if (repositories.length === 0) {
    return undefined;
  }

  const activeFile = vscode.window.activeTextEditor?.document.uri;
  if (!activeFile) {
    return repositories[0];
  }

  const activePath = activeFile.fsPath.toLowerCase();
  return repositories.find((repository) => {
    const rootPath = repository.rootUri.fsPath.toLowerCase();
    return activePath === rootPath || activePath.startsWith(`${rootPath}/`) || activePath.startsWith(`${rootPath}\\`);
  }) ?? repositories[0];
}
