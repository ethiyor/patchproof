from __future__ import annotations

from backend.config import Settings


class TestGitHubAppSettings:
    def test_defaults_are_empty_for_github_app_config(self, monkeypatch):
        monkeypatch.delenv("GITHUB_APP_ID", raising=False)
        monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY_PATH", raising=False)
        monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY", raising=False)
        monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
        monkeypatch.delenv("SERVE_DASHBOARD", raising=False)
        monkeypatch.delenv("CORS_ORIGINS", raising=False)

        settings = Settings(database_url="", _env_file=None)

        assert settings.github_app_id == ""
        assert settings.github_app_private_key_path == ""
        assert settings.github_app_private_key == ""
        assert settings.github_webhook_secret == ""
        assert settings.serve_dashboard is True
        assert "http://localhost:5173" in settings.parsed_cors_origins

    def test_reads_github_app_config_from_environment(self, monkeypatch):
        monkeypatch.setenv("GITHUB_APP_ID", "123456")
        monkeypatch.setenv(
            "GITHUB_APP_PRIVATE_KEY_PATH",
            "./secrets/patchproof-github-app.private-key.pem",
        )
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "inline-private-key")
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "local-webhook-secret")
        monkeypatch.setenv("SERVE_DASHBOARD", "false")
        monkeypatch.setenv("CORS_ORIGINS", "https://patchproof.onrender.com,http://localhost:5173")

        settings = Settings(database_url="", _env_file=None)

        assert settings.github_app_id == "123456"
        assert settings.github_app_private_key_path == "./secrets/patchproof-github-app.private-key.pem"
        assert settings.github_app_private_key == "inline-private-key"
        assert settings.github_webhook_secret == "local-webhook-secret"
        assert settings.serve_dashboard is False
        assert settings.parsed_cors_origins == [
            "https://patchproof.onrender.com",
            "http://localhost:5173",
        ]
