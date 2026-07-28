from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables and .env.

    All values have safe defaults so the app starts without any .env file.
    Override in production by setting the corresponding environment variables.
    """

    # Database
    database_url: str = ""

    # External APIs
    openai_api_key: str = ""
    github_token: str = ""

    # GitHub App webhooks/authentication
    github_app_id: str = ""
    github_app_private_key_path: str = ""
    github_app_private_key: str = ""
    github_webhook_secret: str = ""

    # Security
    secret_key: str = "changeme-in-production"

    # App behaviour
    debug: bool = False
    serve_dashboard: bool = True
    cors_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "http://localhost:8000,"
        "http://127.0.0.1:8000"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",        # ignore unknown env vars silently
        case_sensitive=False,  # DATABASE_URL and database_url both work
    )

    @property
    def parsed_cors_origins(self) -> list[str]:
        """Return comma-separated CORS origins as a cleaned list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Return the cached Settings instance.

    ``@lru_cache`` means this is computed once per process.
    Tests that need different settings should clear the cache with
    ``get_settings.cache_clear()`` before patching.
    """
    return Settings()
