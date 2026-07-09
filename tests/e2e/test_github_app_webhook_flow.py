from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from backend.config import Settings
from backend.main import app
from backend.services.webhook_verifier import build_signature

SECRET = "test-webhook-secret"


def _settings_with_secret() -> Settings:
    return Settings(database_url="", github_webhook_secret=SECRET, _env_file=None)


def _pull_request_payload(action: str) -> bytes:
    return json.dumps(
        {
            "action": action,
            "installation": {"id": 12345},
            "repository": {"full_name": "ethiyor/patchproof"},
            "pull_request": {
                "number": 2,
                "body": "Task: Verify PatchProof GitHub App end-to-end flow.",
            },
        },
        separators=(",", ":"),
    ).encode("utf-8")


@pytest.mark.parametrize("action", ["opened", "synchronize"])
def test_pull_request_events_accept_and_schedule_background_analysis(action: str):
    payload = _pull_request_payload(action)
    headers = {
        "X-GitHub-Event": "pull_request",
        "X-Hub-Signature-256": build_signature(payload, SECRET),
    }

    with patch("backend.api.github_webhook.get_settings", return_value=_settings_with_secret()), \
        patch("backend.api.github_webhook.process_pull_request_webhook") as process_mock:
        response = TestClient(app).post("/github/webhook", content=payload, headers=headers)

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
    process_mock.assert_called_once()
    event = process_mock.call_args.args[0]
    assert event.action == action
    assert event.installation_id == 12345
    assert event.repo_full_name == "ethiyor/patchproof"
    assert event.pr_number == 2
    assert event.pr_body == "Task: Verify PatchProof GitHub App end-to-end flow."