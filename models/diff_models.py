from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Hunk(BaseModel):
    """A single contiguous changed block within a file."""

    header: str  # the @@ -a,b +c,d @@ line
    lines: list[str]  # all lines in the hunk (context, additions, deletions)
    additions: int
    deletions: int


class ParsedFile(BaseModel):
    """A single file entry from a unified diff."""

    path: str
    old_path: str | None = None  # only set for renames
    status: Literal["added", "modified", "deleted", "renamed"] = "modified"
    language: str | None = None  # detected from file extension
    additions: int = 0
    deletions: int = 0
    hunks: list[Hunk] = []
    risk_flags: list[str] = []  # matched risky path pattern names
    is_test_file: bool = False


class ParsedDiff(BaseModel):
    """The full result of parsing a unified diff."""

    files: list[ParsedFile]
    total_files: int
    total_additions: int
    total_deletions: int
    has_test_changes: bool
    risky_files: list[str]  # paths of files that matched at least one risk pattern
