from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from backend.config import Settings
from backend.services.github_app import GitHubAppClient


FIXED_NOW = datetime(2026, 7, 8, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def private_key_pair(tmp_path):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    key_path = tmp_path / "github-app.private-key.pem"
    key_path.write_bytes(private_pem)
    return key_path, public_pem


@pytest.fixture
def github_app_settings(private_key_pair):
    key_path, _ = private_key_pair
    return Settings(
        database_url="",
        github_app_id="4235946",
        github_app_private_key_path=str(key_path),
        github_webhook_secret="test-secret",
        _env_file=None,
    )


def test_create_app_jwt_uses_app_id_and_rs256(github_app_settings, private_key_pair):
    _, public_pem = private_key_pair
    client = GitHubAppClient(settings=github_app_settings, now_fn=lambda: FIXED_NOW)

    token = client.create_app_jwt()
    header = jwt.get_unverified_header(token)
    claims = jwt.decode(
        token,
        public_pem,
        algorithms=["RS256"],
        options={"verify_exp": False, "verify_iat": False},
    )

    assert header["alg"] == "RS256"
    assert claims["iss"] == "4235946"
    assert claims["iat"] == int(FIXED_NOW.timestamp())
    assert claims["exp"] == int((FIXED_NOW + timedelta(seconds=60)).timestamp())


def test_get_installation_token_posts_to_github_and_returns_token(github_app_settings):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            201,
            json={
                "token": "installation-token-1",
                "expires_at": "2026-07-08T13:00:00Z",
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = GitHubAppClient(
        settings=github_app_settings,
        http_client=http_client,
        now_fn=lambda: FIXED_NOW,
    )

    token = client.get_installation_token(98765)

    assert token == "installation-token-1"
    assert len(requests) == 1
    assert str(requests[0].url) == "https://api.github.com/app/installations/98765/access_tokens"
    assert requests[0].method == "POST"
    assert requests[0].headers["authorization"].startswith("Bearer ")
    assert requests[0].headers["x-github-api-version"] == "2022-11-28"


def test_get_installation_token_reuses_cached_token_when_fresh(github_app_settings):
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(
            201,
            json={
                "token": f"installation-token-{call_count}",
                "expires_at": "2026-07-08T13:00:00Z",
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = GitHubAppClient(
        settings=github_app_settings,
        http_client=http_client,
        now_fn=lambda: FIXED_NOW,
    )

    first = client.get_installation_token(42)
    second = client.get_installation_token(42)

    assert first == "installation-token-1"
    assert second == "installation-token-1"
    assert call_count == 1


def test_get_installation_token_refreshes_when_less_than_60_seconds_remain(github_app_settings):
    now_values = iter([
        FIXED_NOW,
        FIXED_NOW + timedelta(minutes=59, seconds=30),
        FIXED_NOW + timedelta(minutes=59, seconds=30),
    ])
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(
            201,
            json={
                "token": f"installation-token-{call_count}",
                "expires_at": "2026-07-08T13:00:00Z",
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = GitHubAppClient(
        settings=github_app_settings,
        http_client=http_client,
        now_fn=lambda: next(now_values),
    )

    first = client.get_installation_token(42)
    second = client.get_installation_token(42)

    assert first == "installation-token-1"
    assert second == "installation-token-2"
    assert call_count == 2


def test_get_installation_token_raises_on_github_error(github_app_settings):
    http_client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(403, json={"message": "Forbidden"}))
    )
    client = GitHubAppClient(
        settings=github_app_settings,
        http_client=http_client,
        now_fn=lambda: FIXED_NOW,
    )

    with pytest.raises(RuntimeError, match="HTTP 403"):
        client.get_installation_token(42)


def test_create_app_jwt_can_read_private_key_from_environment(private_key_pair):
    key_path, public_pem = private_key_pair
    private_key_content = key_path.read_text(encoding="utf-8")
    settings = Settings(
        database_url="",
        github_app_id="4235946",
        github_app_private_key=private_key_content,
        _env_file=None,
    )
    client = GitHubAppClient(settings=settings, now_fn=lambda: FIXED_NOW)

    token = client.create_app_jwt()
    claims = jwt.decode(
        token,
        public_pem,
        algorithms=["RS256"],
        options={"verify_exp": False, "verify_iat": False},
    )

    assert claims["iss"] == "4235946"


def test_create_app_jwt_normalizes_escaped_newlines_in_private_key(private_key_pair):
    key_path, public_pem = private_key_pair
    escaped_private_key = key_path.read_text(encoding="utf-8").replace("\n", "\\n")
    settings = Settings(
        database_url="",
        github_app_id="4235946",
        github_app_private_key=escaped_private_key,
        _env_file=None,
    )
    client = GitHubAppClient(settings=settings, now_fn=lambda: FIXED_NOW)

    token = client.create_app_jwt()
    claims = jwt.decode(
        token,
        public_pem,
        algorithms=["RS256"],
        options={"verify_exp": False, "verify_iat": False},
    )

    assert claims["iss"] == "4235946"


def test_create_app_jwt_requires_app_id(private_key_pair):
    key_path, _ = private_key_pair
    settings = Settings(
        database_url="",
        github_app_id="",
        github_app_private_key_path=str(key_path),
        _env_file=None,
    )
    client = GitHubAppClient(settings=settings, now_fn=lambda: FIXED_NOW)

    with pytest.raises(RuntimeError, match="GITHUB_APP_ID"):
        client.create_app_jwt()


def test_create_app_jwt_requires_private_key_configuration():
    settings = Settings(
        database_url="",
        github_app_id="4235946",
        github_app_private_key_path="",
        github_app_private_key="",
        _env_file=None,
    )
    client = GitHubAppClient(settings=settings, now_fn=lambda: FIXED_NOW)

    with pytest.raises(RuntimeError, match="GITHUB_APP_PRIVATE_KEY"):
        client.create_app_jwt()


def test_create_app_jwt_requires_existing_private_key():
    settings = Settings(
        database_url="",
        github_app_id="4235946",
        github_app_private_key_path="missing-key.pem",
        _env_file=None,
    )
    client = GitHubAppClient(settings=settings, now_fn=lambda: FIXED_NOW)

    with pytest.raises(RuntimeError, match="private key file does not exist"):
        client.create_app_jwt()


def test_default_clients_share_installation_token_cache():
    assert GitHubAppClient()._installation_token_cache is GitHubAppClient()._installation_token_cache
