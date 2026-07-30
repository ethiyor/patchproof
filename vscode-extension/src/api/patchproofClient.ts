import * as vscode from "vscode";

export type PatchProofReviewResponse = {
  review_id: string;
  status: string;
  report_markdown: string;
  risk_score: number;
  risk_level: string;
  merge_recommendation: string;
};

type ReviewLocalChangesInput = {
  task: string;
  diff: string;
  repoName: string;
  branch: string;
};

export async function reviewLocalChanges(input: ReviewLocalChangesInput): Promise<PatchProofReviewResponse> {
  const apiUrl = getApiUrl();
  const response = await fetch(`${apiUrl}/reviews/local`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      task: input.task,
      diff: input.diff,
      repo_name: input.repoName,
      branch: input.branch,
      changed_files: [],
    }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`PatchProof backend returned ${response.status}: ${body || response.statusText}`);
  }

  return await response.json() as PatchProofReviewResponse;
}

export function getApiUrl(): string {
  const configured = vscode.workspace.getConfiguration("patchproof").get<string>("apiUrl");
  return (configured || "http://patchproof-alb-1732344178.us-east-2.elb.amazonaws.com").replace(/\/+$/, "");
}
