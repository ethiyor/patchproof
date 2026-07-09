import httpx
import typer
from pathlib import Path

from cli.config_loader import get_openai_api_key, get_patchproof_api_url
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


def _write_local_review_report(
    *,
    task_text: str,
    diff_result,
    output: Path,
) -> None:
    """Run the original in-process analysis path and write a report."""
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


def _try_backend_review(
    *,
    api_url: str,
    task_text: str,
    diff_result,
    output: Path,
) -> bool:
    """POST the local review to the backend. Return False when it is unreachable."""
    payload = {
        "task": task_text,
        "diff": diff_result.raw,
        "repo_name": diff_result.repo_name,
        "branch": diff_result.branch,
    }
    endpoint = f"{api_url}/reviews/local"

    try:
        response = httpx.post(endpoint, json=payload, timeout=60.0)
    except httpx.RequestError as exc:
        typer.echo(
            f"Backend unavailable at {api_url} ({exc.__class__.__name__}); running offline analysis.",
            err=True,
        )
        return False

    if response.status_code >= 400:
        typer.echo(f"Error: backend review failed with HTTP {response.status_code}.", err=True)
        detail = response.text.strip()
        if detail:
            typer.echo(detail[:500], err=True)
        raise typer.Exit(code=1)

    try:
        data = response.json()
    except ValueError:
        typer.echo("Error: backend returned a non-JSON response.", err=True)
        raise typer.Exit(code=1)

    report = data.get("report_markdown")
    review_id = data.get("review_id")
    if not isinstance(report, str) or not report:
        typer.echo("Error: backend response did not include report_markdown.", err=True)
        raise typer.Exit(code=1)
    if not isinstance(review_id, str) or not review_id:
        typer.echo("Error: backend response did not include review_id.", err=True)
        raise typer.Exit(code=1)

    output.write_text(report, encoding="utf-8")
    typer.echo(f"Review saved: {review_id}")
    return True


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

    api_url = get_patchproof_api_url()
    if api_url:
        if _try_backend_review(
            api_url=api_url,
            task_text=task_text,
            diff_result=diff_result,
            output=output,
        ):
            typer.echo(f"Report  : {output}  ✓")
            return
    else:
        typer.echo("Backend : offline mode")

    _write_local_review_report(
        task_text=task_text,
        diff_result=diff_result,
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
