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
