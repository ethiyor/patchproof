import typer
from pathlib import Path

from cli.git_client import collect_diff
from core.diff_parser import parse_diff
from core.risk_scorer import compute_risk
from core.report_generator import write_report

app = typer.Typer(
    name="patchproof",
    help="PatchProof — verify AI-generated code changes before merging.",
    no_args_is_help=True,
)


@app.command()
def review(
    task: Path = typer.Option(
        ...,
        "--task",
        "-t",
        help="Path to a file containing the task description.",
        exists=True,
        readable=True,
    ),
    diff: Path = typer.Option(
        None,
        "--diff",
        help="Path to a saved .diff file. If omitted, the working tree diff is used.",
    ),
    staged: bool = typer.Option(
        False,
        "--staged",
        help="Use only staged (indexed) changes instead of the full working tree diff.",
    ),
    output: Path = typer.Option(
        Path("patchproof-report.md"),
        "--output",
        "-o",
        help="Where to write the report.",
    ),
) -> None:
    """Analyze the current Git diff against a task description and write a merge-readiness report."""
    task_text = task.read_text(encoding="utf-8").strip()

    diff_result = collect_diff(staged_only=staged, diff_file=diff)

    typer.echo(f"Repo    : {diff_result.repo_name}  [{diff_result.branch}]")
    typer.echo(f"Diff    : {diff_result}")

    parsed = parse_diff(diff_result.raw)
    risk = compute_risk(parsed)

    typer.echo(f"Risk    : {risk}")

    write_report(
        diff=parsed,
        risk=risk,
        task_text=task_text,
        repo_name=diff_result.repo_name,
        branch=diff_result.branch,
        output=output,
    )

    typer.echo(f"Report  : {output}  ✓")


@app.command(name="review-pr")
def review_pr(
    pr_url: str = typer.Argument(..., help="GitHub PR URL to review."),
    task: Path = typer.Option(
        None,
        "--task",
        "-t",
        help="Path to a task description file. Falls back to PR body if omitted.",
    ),
    output: Path = typer.Option(
        Path("patchproof-report.md"),
        "--output",
        "-o",
        help="Where to write the report.",
    ),
) -> None:
    """Fetch a GitHub PR diff and write a merge-readiness report. (Phase 3)"""
    typer.echo("review-pr coming in Phase 3.", err=True)
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()


if __name__ == "__main__":
    app()
