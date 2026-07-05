from __future__ import annotations

import logging
import os
import re

import httpx

from models.github_models import PRMetadata

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.github.com"
_TIMEOUT = 30.0
_API_VERSION = "2022-11-28"
_ACCEPT_JSON = "application/vnd.github+json"
_ACCEPT_DIFF = "application/vnd.github.diff"

# Matches: https://github.com/{owner}/{repo}/pull/{number}[/]
_PR_URL_RE = re.compile(
    r"^https://github\.com/([^/]+)/([^/]+)/pull/(\d+)/?$"
)

# Matches: Closes #42, Fixes #7, Resolves #100 (case-insensitive)
_CLOSES_RE = re.compile(
    r"(?:closes|fixes|resolves)\s+#(\d+)", re.IGNORECASE
)


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

    # ------------------------------------------------------------------
    # PR metadata
    # ------------------------------------------------------------------

    def fetch_pr_metadata(
        self, owner: str, repo: str, pr_number: int
    ) -> PRMetadata:
        """
        Fetch metadata for a pull request and return a PRMetadata model.

        If the PR body contains ``Closes #N`` / ``Fixes #N`` / ``Resolves #N``,
        the linked issue body is fetched and included (best-effort — failure is
        silently ignored so the pipeline can continue without the issue body).
        """
        data = self.get(f"/repos/{owner}/{repo}/pulls/{pr_number}")

        body: str = data.get("body") or ""

        # Try to fetch the linked issue body
        linked_issue_body: str | None = None
        match = _CLOSES_RE.search(body)
        if match:
            issue_number = int(match.group(1))
            try:
                issue_data = self.get(
                    f"/repos/{owner}/{repo}/issues/{issue_number}"
                )
                linked_issue_body = issue_data.get("body") or None
            except RuntimeError as exc:
                logger.debug("Could not fetch linked issue #%d: %s", issue_number, exc)

        return PRMetadata(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            title=data.get("title", ""),
            body=body,
            author=data["user"]["login"],
            base_branch=data["base"]["ref"],
            head_branch=data["head"]["ref"],
            state=data["state"],
            linked_issue_body=linked_issue_body,
        )


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------

def parse_pr_url(url: str) -> tuple[str, str, int]:
    """
    Parse a GitHub PR URL into (owner, repo, pr_number).

    Accepts: https://github.com/{owner}/{repo}/pull/{number}[/]

    Raises:
        ValueError: if the URL does not match the expected format.
    """
    m = _PR_URL_RE.match(url.strip())
    if not m:
        raise ValueError(
            f"Invalid GitHub PR URL format: {url!r}\n"
            "Expected: https://github.com/owner/repo/pull/123"
        )
    return m.group(1), m.group(2), int(m.group(3))


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
