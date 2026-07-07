from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LocalReviewRequest(BaseModel):
    """Request body for POST /reviews/local."""

    task: str = Field(..., description="Plain-English task description (contents of task.txt).")
    diff: str = Field(..., description="Raw unified diff string from git diff HEAD or similar.")
    repo_name: str = Field("unknown", description="Repository name for the report header.")
    branch: str = Field("unknown", description="Branch name for the report header.")
    changed_files: list[str] = Field(default_factory=list, description="Optional list of changed file paths.")
    test_output: str | None = Field(None, description="Optional test runner output (pytest, etc.).")


class GithubPRReviewRequest(BaseModel):
    """Request body for POST /reviews/github-pr."""

    pr_url: str = Field(..., description="GitHub pull request URL, e.g. https://github.com/owner/repo/pull/42.")
    task: str | None = Field(None, description="Optional task text. Falls back to PR body when omitted.")


class ReviewResponse(BaseModel):
    """Response body returned by review endpoints."""

    review_id: str
    status: str                   # "completed" | "failed"
    report_markdown: str
    risk_score: int
    risk_level: str               # "low" | "medium" | "high" | "critical"
    merge_recommendation: str     # "ready" | "ready_with_comments" | "needs_changes" | "do_not_merge"


class ReviewFindingResponse(BaseModel):
    """Finding item returned by GET /reviews/{review_id}."""

    category: str | None = None
    severity: str | None = None
    title: str
    description: str | None = None
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    evidence: str | None = None
    suggestion: str | None = None


class RequirementCheckResponse(BaseModel):
    """Requirement check item returned by GET /reviews/{review_id}."""

    requirement_text: str
    status: str | None = None
    evidence: str | None = None
    reason: str | None = None


class ChangedFileResponse(BaseModel):
    """Changed file item returned by GET /reviews/{review_id}."""

    file_path: str
    status: str | None = None
    language: str | None = None
    additions: int
    deletions: int
    risk_flags: list[str] | None = None


class ReviewDetailResponse(BaseModel):
    """Full saved review returned by GET /reviews/{review_id}."""

    review_id: str
    created_at: datetime
    task_text: str | None = None
    risk_score: int | None = None
    risk_level: str | None = None
    merge_recommendation: str | None = None
    report_markdown: str | None = None
    findings: list[ReviewFindingResponse] = Field(default_factory=list)
    requirement_checks: list[RequirementCheckResponse] = Field(default_factory=list)
    changed_files: list[ChangedFileResponse] = Field(default_factory=list)
