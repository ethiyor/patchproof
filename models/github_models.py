from __future__ import annotations

from pydantic import BaseModel


class PRMetadata(BaseModel):
    """Structured metadata for a GitHub pull request."""

    owner: str
    repo: str
    pr_number: int
    title: str
    body: str
    author: str
    base_branch: str
    head_branch: str
    state: str
    linked_issue_body: str | None = None  # body of issue referenced by Closes/Fixes #N
