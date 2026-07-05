from __future__ import annotations

import logging

from pydantic import ValidationError

from llm.client import call_llm
from llm.prompts import STEP1_SYSTEM, step1_user
from models.llm_outputs import RequirementsOutput

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 2


def analyze_task(task_text: str) -> RequirementsOutput:
    """
    LLM Step 1: extract structured requirements from a task description.

    Retries once if the LLM returns an empty requirements list or a response
    that fails Pydantic validation.

    Args:
        task_text: Plain-English task description (contents of task.txt).

    Returns:
        Validated RequirementsOutput with requirements, test cases, and risk domains.

    Raises:
        RuntimeError: if both attempts fail or the response is consistently invalid.
    """
    messages = [
        {"role": "system", "content": STEP1_SYSTEM},
        {"role": "user", "content": step1_user(task_text)},
    ]

    last_error: Exception | None = None

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            raw = call_llm(messages)
            result = RequirementsOutput(**raw)

            if not result.requirements:
                raise ValueError(
                    "LLM returned an empty requirements list. "
                    "The task description may be too vague."
                )

            logger.debug(
                "Step 1 complete: %d requirements extracted",
                len(result.requirements),
            )
            return result

        except (ValidationError, ValueError, KeyError) as exc:
            last_error = exc
            logger.warning(
                "Step 1 attempt %d/%d failed: %s",
                attempt, _MAX_ATTEMPTS, exc,
            )

    raise RuntimeError(
        "Could not extract requirements from the task description. "
        "Try writing a more specific task. "
        f"Last error: {last_error}"
    )
