import typer
from pathlib import Path

from cli.config_loader import get_openai_api_key
from cli.git_client import collect_diff
from cli.github_client import make_github_client, parse_pr_url
from core.diff_parser import parse_diff
from core.risk_scorer import compute_risk
from core.report_generator import write_report, write_full_report

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

    if get_openai_api_key():
        from llm.pipeline import run_pipeline
        typer.echo("Running LLM pipeline...")
        pipeline_result = run_pipeline(
            task_text=task_text,
            diff_text=diff_result.raw,
            parsed_diff=parsed,
            risk=risk,
        )
        write_full_report(
            diff=parsed,
            risk=risk,
            task_text=task_text,
            repo_name=diff_result.repo_name,
            branch=diff_result.branch,
            pipeline_result=pipeline_result,
            output=output,
        )
    else:
        typer.echo("Note: OPENAI_API_KEY not set — writing basic report (Phase 1).", err=True)
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
    """Fetch a GitHub PR diff and write a merge-readiness report."""
    # --- Parse and validate the PR URL ---
    try:
        owner, repo, pr_number = parse_pr_url(pr_url)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    # --- Connect to GitHub ---
    try:
        client = make_github_client()
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    # --- Fetch PR metadata ---
    try:
        metadata = client.fetch_pr_metadata(owner, repo, pr_number)
    except RuntimeError as exc:
        typer.echo(f"Error fetching PR: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"PR      : #{pr_number} — {metadata.title}")
    typer.echo(f"Repo    : {owner}/{repo}  [{metadata.head_branch} → {metadata.base_branch}]")

    # --- Resolve task text ---
    if task is not None:
        task_text = task.read_text(encoding="utf-8").strip()
    elif metadata.body.strip():
        task_text = metadata.body.strip()
        typer.echo("Task    : (using PR body)")
    elif metadata.linked_issue_body:
        task_text = metadata.linked_issue_body.strip()
        typer.echo("Task    : (using linked issue body)")
    else:
        typer.echo(
            "Error: no task provided. Use --task or add a description to the PR body.",
            err=True,
        )
        raise typer.Exit(code=1)

    # --- Fetch the diff ---
    try:
        raw_diff = client.fetch_pr_diff(owner, repo, pr_number)
    except RuntimeError as exc:
        typer.echo(f"Error fetching diff: {exc}", err=True)
        raise typer.Exit(code=1)

    if not raw_diff:
        typer.echo("No file changes found in this PR.", err=True)
        raise typer.Exit(code=1)

    # --- Parse + score ---
    parsed = parse_diff(raw_diff)
    risk = compute_risk(parsed)

    typer.echo(f"Diff    : {parsed.total_files} files changed (+{parsed.total_additions} -{parsed.total_deletions})")
    typer.echo(f"Risk    : {risk}")

    # --- Run pipeline or basic report ---
    if get_openai_api_key():
        from llm.pipeline import run_pipeline
        typer.echo("Running LLM pipeline...")
        pipeline_result = run_pipeline(
            task_text=task_text,
            diff_text=raw_diff,
            parsed_diff=parsed,
            risk=risk,
        )
        write_full_report(
            diff=parsed,
            risk=risk,
            task_text=task_text,
            repo_name=f"{owner}/{repo}",
            branch=f"#{pr_number}",
            pipeline_result=pipeline_result,
            output=output,
        )
    else:
        typer.echo("Note: OPENAI_API_KEY not set — writing basic report.", err=True)
        write_report(
            diff=parsed,
            risk=risk,
            task_text=task_text,
            repo_name=f"{owner}/{repo}",
            branch=f"#{pr_number}",
            output=output,
        )

    typer.echo(f"Report  : {output}  ✓")


if __name__ == "__main__":
    app()
