from __future__ import annotations

from unittest.mock import patch

from starlette.testclient import TestClient

from backend.config import Settings
from backend.main import app
from backend.services.webhook_verifier import build_signature, verify_signature

SECRET = "test-webhook-secret"
PAYLOAD = (
    b'{"action":"opened","installation":{"id":12345},'
    b'"repository":{"full_name":"ethiyor/patchproof"},'
    b'"pull_request":{"number":42,"body":"Add PDF upload support"}}'
)


def _settings_with_secret() -> Settings:
    return Settings(database_url="", github_webhook_secret=SECRET, _env_file=None)


class TestWebhookSignatureVerifier:
    def test_accepts_valid_sha256_signature(self):
        signature = build_signature(PAYLOAD, SECRET)

        assert verify_signature(PAYLOAD, signature, SECRET) is True

    def test_rejects_wrong_signature(self):
        assert verify_signature(PAYLOAD, "sha256=not-the-right-digest", SECRET) is False

    def test_rejects_missing_signature(self):
        assert verify_signature(PAYLOAD, None, SECRET) is False

    def test_rejects_non_sha256_signature_header(self):
        assert verify_signature(PAYLOAD, "sha1=abc123", SECRET) is False

    def test_rejects_missing_secret(self):
        signature = build_signature(PAYLOAD, SECRET)

        assert verify_signature(PAYLOAD, signature, "") is False


class TestGitHubWebhookEndpoint:
    def setup_method(self):
        self.settings_patch = patch(
            "backend.api.github_webhook.get_settings",
            return_value=_settings_with_secret(),
        )
        self.process_patch = patch("backend.api.github_webhook.process_pull_request_webhook")
        self.settings_patch.start()
        self.process_mock = self.process_patch.start()
        self.client = TestClient(app)

    def teardown_method(self):
        self.process_patch.stop()
        self.settings_patch.stop()

    def _headers(self, payload: bytes, event: str = "pull_request") -> dict[str, str]:
        return {
            "X-Hub-Signature-256": build_signature(payload, SECRET),
            "X-GitHub-Event": event,
        }

    def test_valid_pull_request_webhook_returns_202_and_schedules_background_task(self):
        response = self.client.post(
            "/github/webhook",
            content=PAYLOAD,
            headers=self._headers(PAYLOAD),
        )

        assert response.status_code == 202
        assert response.json() == {"status": "accepted"}
        self.process_mock.assert_called_once()
        event = self.process_mock.call_args.args[0]
        assert event.installation_id == 12345
        assert event.repo_full_name == "ethiyor/patchproof"
        assert event.pr_number == 42
        assert event.pr_body == "Add PDF upload support"

    def test_missing_signature_returns_403(self):
        response = self.client.post(
            "/github/webhook",
            content=PAYLOAD,
            headers={"X-GitHub-Event": "pull_request"},
        )

        assert response.status_code == 403
        assert response.json() == {"detail": "Invalid GitHub webhook signature."}
        self.process_mock.assert_not_called()

    def test_wrong_signature_returns_403(self):
        response = self.client.post(
            "/github/webhook",
            content=PAYLOAD,
            headers={
                "X-Hub-Signature-256": "sha256=wrong",
                "X-GitHub-Event": "pull_request",
            },
        )

        assert response.status_code == 403
        self.process_mock.assert_not_called()

    def test_valid_non_pull_request_event_is_ignored(self):
        response = self.client.post(
            "/github/webhook",
            content=PAYLOAD,
            headers=self._headers(PAYLOAD, event="ping"),
        )

        assert response.status_code == 200
        assert response.json() == {"status": "ignored", "event": "ping"}
        self.process_mock.assert_not_called()

    def test_valid_pull_request_webhook_requires_json_payload(self):
        payload = b"not-json"

        response = self.client.post(
            "/github/webhook",
            content=payload,
            headers=self._headers(payload),
        )

        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid GitHub webhook JSON payload."}
        self.process_mock.assert_not_called()

    def test_valid_pull_request_webhook_requires_required_fields(self):
        payload = b'{"action":"opened"}'

        response = self.client.post(
            "/github/webhook",
            content=payload,
            headers=self._headers(payload),
        )

        assert response.status_code == 400
        assert "missing installation" in response.json()["detail"]
        self.process_mock.assert_not_called()

    def test_missing_configured_secret_returns_500(self):
        with patch(
            "backend.api.github_webhook.get_settings",
            return_value=Settings(database_url="", github_webhook_secret="", _env_file=None),
        ):
            response = self.client.post(
                "/github/webhook",
                content=PAYLOAD,
                headers=self._headers(PAYLOAD),
            )

        assert response.status_code == 500
        assert response.json() == {"detail": "GitHub webhook secret is not configured."}
        self.process_mock.assert_not_called()