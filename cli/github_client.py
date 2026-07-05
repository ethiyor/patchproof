from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.github.com"
_TIMEOUT = 30.0
_API_VERSION = "2022-11-28"
_ACCEPT_JSON = "application/vnd.github+json"
_ACCEPT_DIFF = "application/vnd.github.diff"


class GitHubClient:
    """
    Thin synchronous wrapper around the GitHub REST API.

    Every request carries:
      Authorization: Bearer <token>
      Accept: application/vnd.github+json   (or overridden per call)
      X-GitHub-Api-Version: 2022-11-28
    """

    def __init__(self, token: str) -> None:
        self._token = token
        self._base_headers = {
            "Authorization": f"Bearer {token}",
            "Accept": _ACCEPT_JSON,
            "X-GitHub-Api-Version": _API_VERSION,
        }

    # ------------------------------------------------------------------
    # Core transport
    # ------------------------------------------------------------------

    def _request(self, path: str, accept: str | None = None) -> httpx.Response:
        headers = {**self._base_headers}
        if accept:
            headers["Accept"] = accept

        with httpx.Client(timeout=_TIMEOUT) as client:
            response = client.get(f"{_BASE_URL}{path}", headers=headers)

        self._raise_for_status(response, path)
        return response

    @staticmethod
    def _raise_for_status(response: httpx.Response, path: str) -> None:
        if response.status_code == 401:
            raise RuntimeError(
                "GitHub token is invalid or expired. "
                "Regenerate it at https://github.com/settings/tokens"
            )
        if response.status_code == 403:
            raise RuntimeError(
                "GitHub API rate limit exceeded or insufficient permissions. "
                "Wait a moment or check the token's scopes."
            )
        if response.status_code == 404:
            raise RuntimeError(f"GitHub resource not found: {path}")
        response.raise_for_status()

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def get(self, path: str) -> dict:
        """Fetch a JSON resource. Returns the parsed response body."""
        return self._request(path).json()

    def get_raw(self, path: str, accept: str) -> str:
        """Fetch a resource and return raw text (used for diff content)."""
        return self._request(path, accept=accept).text

    def get_diff(self, path: str) -> str:
        """Fetch a unified diff for a PR or commit."""
        return self.get_raw(path, accept=_ACCEPT_DIFF)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_github_client() -> GitHubClient:
    """
    Create a GitHubClient using GITHUB_TOKEN from the environment.

    Raises RuntimeError if the token is missing.
    Never logs the full token — only the first 4 characters.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN is not set. "
            "Add it to your .env file or export it in your shell."
        )
    logger.debug("GitHub client ready (token: %s****)", token[:4])
    return GitHubClient(token)
