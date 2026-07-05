from __future__ import annotations

import logging

from pydantic import ValidationError

from llm.client import call_llm
from llm.prompts import STEP2_SYSTEM, step2_user
from models.llm_outputs import DiffSummaryOutput

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 2


def summarize_diff(diff_text: str) -> DiffSummaryOutput:
    """
    LLM Step 2: summarise what changed in a unified diff.

    Large diffs are truncated to 60 000 characters before being sent
    (handled inside ``step2_user``). Retries once on validation failure.

    Args:
        diff_text: Raw unified diff string (e.g. from DiffResult.raw).

    Returns:
        Validated DiffSummaryOutput with a prose summary and structured lists.

    Raises:
        RuntimeError: if both attempts return an invalid response.
    """
    messages = [
        {"role": "system", "content": STEP2_SYSTEM},
        {"role": "user", "content": step2_user(diff_text)},
    ]

    last_error: Exception | None = None

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            raw = call_llm(messages)
            result = DiffSummaryOutput(**raw)
            logger.debug(
                "Step 2 complete: %d implemented areas, %d side effects",
                len(result.implemented_areas),
                len(result.possible_side_effects),
            )
            return result

        except (ValidationError, KeyError, TypeError) as exc:
            last_error = exc
            logger.warning(
                "Step 2 attempt %d/%d failed: %s",
                attempt, _MAX_ATTEMPTS, exc,
            )

    raise RuntimeError(
        f"Could not summarise the diff after {_MAX_ATTEMPTS} attempts. "
        f"Last error: {last_error}"
    )
