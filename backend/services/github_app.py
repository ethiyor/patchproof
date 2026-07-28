from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable, ClassVar

import httpx
import jwt

from backend.config import Settings, get_settings

GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"
JWT_ALGORITHM = "RS256"
JWT_LIFETIME_SECONDS = 60
TOKEN_REFRESH_WINDOW_SECONDS = 60


@dataclass(frozen=True)
class InstallationToken:
    """Cached GitHub installation token and its expiry time."""

    token: str
    expires_at: datetime


class GitHubAppClient:
    """Authenticate as the GitHub App and fetch installation access tokens."""

    _shared_installation_token_cache: ClassVar[dict[int, InstallationToken]] = {}

    def __init__(
        self,
        settings: Settings | None = None,
        http_client: httpx.Client | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.http_client = http_client or httpx.Client(timeout=30.0)
        self._owns_http_client = http_client is None
        self.now_fn = now_fn or (lambda: datetime.now(UTC))
        if settings is None and http_client is None and now_fn is None:
            self._installation_token_cache = self._shared_installation_token_cache
        else:
            self._installation_token_cache: dict[int, InstallationToken] = {}

    def close(self) -> None:
        if self._owns_http_client:
            self.http_client.close()

    def create_app_jwt(self) -> str:
        """Create a short-lived RS256 JWT for authenticating as the GitHub App."""
        app_id = self.settings.github_app_id.strip()
        if not app_id:
            raise RuntimeError("GITHUB_APP_ID is not configured.")

        private_key = self._read_private_key()
        now = self._now_utc()
        payload = {
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=JWT_LIFETIME_SECONDS)).timestamp()),
            "iss": app_id,
        }
        return jwt.encode(payload, private_key, algorithm=JWT_ALGORITHM)

    def get_installation_token(self, installation_id: int) -> str:
        """Return a cached installation token, refreshing it when near expiry."""
        cached = self._installation_token_cache.get(installation_id)
        if cached and self._is_token_fresh(cached):
            return cached.token

        app_jwt = self.create_app_jwt()
        response = self.http_client.post(
            f"{GITHUB_API_BASE_URL}/app/installations/{installation_id}/access_tokens",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {app_jwt}",
                "X-GitHub-Api-Version": GITHUB_API_VERSION,
            },
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"GitHub installation token request failed with HTTP {response.status_code}."
            ) from exc

        data = response.json()
        token = data.get("token")
        expires_at_raw = data.get("expires_at")
        if not isinstance(token, str) or not token:
            raise RuntimeError("GitHub installation token response did not include a token.")
        if not isinstance(expires_at_raw, str) or not expires_at_raw:
            raise RuntimeError("GitHub installation token response did not include expires_at.")

        expires_at = _parse_github_datetime(expires_at_raw)
        self._installation_token_cache[installation_id] = InstallationToken(
            token=token,
            expires_at=expires_at,
        )
        return token

    def _read_private_key(self) -> str:
        private_key = self.settings.github_app_private_key.strip()
        if private_key:
            return private_key.replace("\\n", "\n")

        private_key_path = self.settings.github_app_private_key_path.strip()
        if not private_key_path:
            raise RuntimeError("GITHUB_APP_PRIVATE_KEY or GITHUB_APP_PRIVATE_KEY_PATH is not configured.")

        path = Path(private_key_path)
        if not path.exists():
            raise RuntimeError(f"GitHub App private key file does not exist: {path}")
        return path.read_text(encoding="utf-8")

    def _is_token_fresh(self, cached: InstallationToken) -> bool:
        refresh_at = cached.expires_at - timedelta(seconds=TOKEN_REFRESH_WINDOW_SECONDS)
        return self._now_utc() < refresh_at

    def _now_utc(self) -> datetime:
        now = self.now_fn()
        if now.tzinfo is None:
            return now.replace(tzinfo=UTC)
        return now.astimezone(UTC)


def _parse_github_datetime(value: str) -> datetime:
    """Parse GitHub's ISO-8601 UTC timestamps."""
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
