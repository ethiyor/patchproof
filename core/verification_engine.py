from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from pydantic import ValidationError

from llm.client import call_llm
from llm.prompts import STEP3_SYSTEM, step3_user
from models.llm_outputs import VerificationResult

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 2
_MAX_DIFF_CHARS = 30_000  # per-requirement diff budget


def _verify_one(
    requirement: str,
    diff_text: str,
    repo_context: str = "",
) -> VerificationResult:
    """
    Verify a single requirement against the diff.

    Retries once if the LLM response fails Pydantic validation (which includes
    the evidence rule: satisfied/partially_satisfied require evidence citations).

    If both attempts fail, downgrades the status to ``unclear`` rather than
    raising — a degraded result is more useful than a crash.
    """
    # Truncate diff to stay within per-requirement token budget.
    truncated_diff = diff_text[:_MAX_DIFF_CHARS]
    if len(diff_text) > _MAX_DIFF_CHARS:
        truncated_diff += "\n[diff truncated]"

    messages = [
        {"role": "system", "content": STEP3_SYSTEM},
        {"role": "user", "content": step3_user(requirement, truncated_diff, repo_context)},
    ]

    last_exc: Exception | None = None

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            raw = call_llm(messages)
            result = VerificationResult(**raw)
            logger.debug(
                "Step 3 | req=%r status=%s evidence=%d",
                requirement[:40],
                result.status,
                len(result.evidence),
            )
            return result

        except (ValidationError, KeyError, TypeError) as exc:
            last_exc = exc
            logger.warning(
                "Step 3 attempt %d/%d failed for req=%r: %s",
                attempt, _MAX_ATTEMPTS, requirement[:40], exc,
            )

    # Both attempts failed — downgrade to "unclear" rather than crashing the
    # entire pipeline over one requirement.
    logger.warning(
        "Step 3 downgrading req=%r to 'unclear' after %d failed attempts",
        requirement[:40], _MAX_ATTEMPTS,
    )
    return VerificationResult(
        requirement=requirement,
        status="unclear",
        evidence=[],
        reason=(
            f"Could not verify this requirement after {_MAX_ATTEMPTS} attempts. "
            f"Last error: {last_exc}"
        ),
    )


def verify_requirements(
    requirements: list[str],
    diff_text: str,
    repo_context: str = "",
    max_workers: int = 1,
) -> list[VerificationResult]:
    """
    Verify all requirements against the diff.

    Args:
        requirements:  List of requirement strings from RequirementsOutput.
        diff_text:     Raw unified diff (from DiffResult.raw).
        repo_context:  Optional extra file content for context (Phase 3+).
        max_workers:   Number of parallel LLM calls. Default 1 (sequential).
                       Set higher to speed up large requirement lists.

    Returns:
        List of VerificationResult, one per requirement, in the same order.
    """
    if not requirements:
        return []

    if max_workers == 1:
        return [
            _verify_one(req, diff_text, repo_context)
            for req in requirements
        ]

    # Parallel execution — preserve original order via index.
    results: list[VerificationResult | None] = [None] * len(requirements)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_verify_one, req, diff_text, repo_context): i
            for i, req in enumerate(requirements)
        }
        for future in as_completed(futures):
            idx = futures[future]
            results[idx] = future.result()

    return results  # type: ignore[return-value]
