from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env from the project root (two levels up from this file: cli/ -> project root)
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=False)


def get_openai_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY")


def get_github_token() -> str | None:
    return os.getenv("GITHUB_TOKEN")


def get_patchproof_api_url() -> str | None:
    """Return the backend API URL, or None when offline mode is requested."""
    raw_value = os.getenv("PATCHPROOF_API_URL")
    if raw_value is None:
        return "http://localhost:8000"

    value = raw_value.strip().rstrip("/")
    return value or None
