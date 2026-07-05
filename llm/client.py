from __future__ import annotations

import json
import logging
import os
import time

from openai import APIConnectionError, APIError, OpenAI, RateLimitError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TEMPERATURE = 0.1
_DEFAULT_MODEL = "gpt-4o"
_DEFAULT_MAX_RETRIES = 2
_RETRY_DELAY = 2.0       # seconds between retries on network/JSON errors
_RATE_LIMIT_DELAY = 5.0  # seconds between retries on rate limit

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _make_client() -> OpenAI:
    """
    Create an OpenAI client using OPENAI_API_KEY from the environment.

    Raises RuntimeError if the key is missing.
    Never logs the full key — only the first 4 characters.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. "
            "Add it to your .env file or export it in your shell."
        )
    logger.debug("OpenAI client created with key %s****", api_key[:4])
    return OpenAI(api_key=api_key)


def _build_response(raw: str) -> dict:
    """Parse the assistant's response string as JSON."""
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def call_llm(
    messages: list[dict],
    model: str = _DEFAULT_MODEL,
    max_retries: int = _DEFAULT_MAX_RETRIES,
) -> dict:
    """
    Call the OpenAI chat completions API in JSON mode.

    Args:
        messages:    List of OpenAI message dicts (role + content).
        model:       Model identifier. Defaults to gpt-4o.
        max_retries: How many times to retry on recoverable errors.

    Returns:
        Parsed JSON dict from the assistant's response.

    Raises:
        RuntimeError: OPENAI_API_KEY missing, non-retryable API error, or
                      all retries exhausted.
    """
    client = _make_client()
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=_TEMPERATURE,
            )

            # Log token usage — never the response content.
            usage = response.usage
            if usage:
                logger.debug(
                    "LLM usage | model=%s prompt=%d completion=%d total=%d",
                    model,
                    usage.prompt_tokens,
                    usage.completion_tokens,
                    usage.total_tokens,
                )

            content = response.choices[0].message.content
            return _build_response(content)

        except APIConnectionError as exc:
            last_error = exc
            logger.warning(
                "LLM attempt %d/%d failed (connection error): %s",
                attempt, max_retries, exc,
            )
            if attempt < max_retries:
                time.sleep(_RETRY_DELAY)

        except RateLimitError as exc:
            last_error = exc
            logger.warning(
                "LLM attempt %d/%d failed (rate limit): %s",
                attempt, max_retries, exc,
            )
            if attempt < max_retries:
                time.sleep(_RATE_LIMIT_DELAY)

        except json.JSONDecodeError as exc:
            last_error = exc
            logger.warning(
                "LLM attempt %d/%d returned invalid JSON: %s",
                attempt, max_retries, exc,
            )
            if attempt < max_retries:
                time.sleep(_RETRY_DELAY)

        except APIError as exc:
            # Auth errors, bad requests — not worth retrying.
            raise RuntimeError(f"OpenAI API error (not retryable): {exc}") from exc

    raise RuntimeError(
        f"LLM call failed after {max_retries} attempt(s). "
        f"Last error: {last_error}"
    )
