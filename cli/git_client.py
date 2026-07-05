from pathlib import Path
from dataclasses import dataclass

import git
from git.exc import InvalidGitRepositoryError


@dataclass
class DiffResult:
    """Raw diff text plus quick stats computed without a full parser."""
    raw: str
    file_count: int
    additions: int
    deletions: int
    repo_name: str
    branch: str

    def __str__(self) -> str:
        return (
            f"{self.file_count} file{'s' if self.file_count != 1 else ''} changed "
            f"(+{self.additions} -{self.deletions})"
        )


def _count_stats(raw_diff: str) -> tuple[int, int, int]:
    """Return (file_count, additions, deletions) from a raw unified diff string."""
    file_count = 0
    additions = 0
    deletions = 0
    for line in raw_diff.splitlines():
        if line.startswith("diff --git"):
            file_count += 1
        elif line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1
    return file_count, additions, deletions


def collect_diff(
    repo_path: Path | None = None,
    staged_only: bool = False,
    diff_file: Path | None = None,
) -> DiffResult:
    """
    Collect a unified diff and return a DiffResult.

    Priority:
      1. If diff_file is provided, read it directly.
      2. If staged_only, diff the index against HEAD.
      3. Otherwise, diff the full working tree against HEAD (staged + unstaged).

    Raises:
      typer.Exit: with a user-facing error message on any Git problem.
    """
    import typer

    # --- Case 1: saved diff file ---
    if diff_file is not None:
        raw = diff_file.read_text(encoding="utf-8", errors="replace")
        file_count, additions, deletions = _count_stats(raw)
        return DiffResult(
            raw=raw,
            file_count=file_count,
            additions=additions,
            deletions=deletions,
            repo_name=diff_file.stem,
            branch="(from file)",
        )

    # --- Case 2 & 3: live Git repo ---
    try:
        repo = git.Repo(
            path=str(repo_path) if repo_path else ".",
            search_parent_directories=True,
        )
    except InvalidGitRepositoryError:
        typer.echo("Error: not inside a Git repository.", err=True)
        raise typer.Exit(code=1)

    # Resolve repo name from remote or folder name
    try:
        remote_url = repo.remotes.origin.url
        repo_name = remote_url.rstrip("/").split("/")[-1].removesuffix(".git")
    except (AttributeError, IndexError):
        repo_name = Path(repo.working_dir).name

    # Resolve current branch name
    try:
        branch = repo.active_branch.name
    except TypeError:
        branch = repo.head.commit.hexsha[:8]  # detached HEAD

    if staged_only:
        raw = repo.git.diff("--cached")
    else:
        try:
            raw = repo.git.diff("HEAD")
        except git.GitCommandError as exc:
            # Brand-new repo with no commits yet — HEAD doesn't exist.
            # Fall back to showing staged changes vs the empty tree.
            if "unknown revision" in str(exc).lower() or "ambiguous argument" in str(exc).lower():
                raw = repo.git.diff("--cached")
            else:
                raise

    if not raw.strip():
        typer.echo("No changes detected. Make some edits or stage some files first.", err=True)
        raise typer.Exit(code=1)

    file_count, additions, deletions = _count_stats(raw)
    return DiffResult(
        raw=raw,
        file_count=file_count,
        additions=additions,
        deletions=deletions,
        repo_name=repo_name,
        branch=branch,
    )
