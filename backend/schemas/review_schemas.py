from __future__ import annotations

from pydantic import BaseModel, Field


class LocalReviewRequest(BaseModel):
    """Request body for POST /reviews/local."""

    task: str = Field(..., description="Plain-English task description (contents of task.txt).")
    diff: str = Field(..., description="Raw unified diff string from git diff HEAD or similar.")
    repo_name: str = Field("unknown", description="Repository name for the report header.")
    branch: str = Field("unknown", description="Branch name for the report header.")
    changed_files: list[str] = Field(default_factory=list, description="Optional list of changed file paths.")
    test_output: str | None = Field(None, description="Optional test runner output (pytest, etc.).")


class ReviewResponse(BaseModel):
    """Response body returned by review endpoints."""

    review_id: str
    status: str                   # "completed" | "failed"
    report_markdown: str
    risk_score: int
    risk_level: str               # "low" | "medium" | "high" | "critical"
    merge_recommendation: str     # "ready" | "ready_with_comments" | "needs_changes" | "do_not_merge"
