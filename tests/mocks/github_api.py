"""
respx mock fixtures for the GitHub REST API.

Usage in tests:
    import respx, httpx
    from tests.mocks.github_api import mock_get_user, mock_pr_metadata, mock_pr_diff

    @respx.mock
    def test_something():
        mock_get_user()
        client = GitHubClient("ghp_fake1234")
        result = client.get("/user")
        assert result["login"] == "ethiyor"
"""

from __future__ import annotations

import respx
import httpx

# ---------------------------------------------------------------------------
# Response body fixtures
# ---------------------------------------------------------------------------

USER_RESPONSE = {
    "login": "ethiyor",
    "id": 12345678,
    "type": "User",
    "name": "Test User",
}

PR_METADATA_RESPONSE = {
    "number": 42,
    "title": "Add PDF upload support",
    "body": "Closes #10\n\nAdds a file upload endpoint with MIME validation.",
    "state": "open",
    "user": {"login": "ethiyor"},
    "base": {"ref": "main"},
    "head": {"ref": "feat/pdf-upload"},
}

PR_DIFF_RESPONSE = """\
diff --git a/backend/routes/upload.py b/backend/routes/upload.py
new file mode 100644
index 0000000..a1b2c3d
--- /dev/null
+++ b/backend/routes/upload.py
@@ -0,0 +1,10 @@
+from fastapi import UploadFile
+
+async def upload_paper(file: UploadFile):
+    content = await file.read()
+    return {"paper_id": "abc123"}
"""

ISSUE_RESPONSE = {
    "number": 10,
    "title": "Support PDF uploads",
    "body": "Users should be able to upload PDF files to the system.",
}

# ---------------------------------------------------------------------------
# Mock helpers — call these inside @respx.mock blocks
# ---------------------------------------------------------------------------

def mock_get_user() -> None:
    respx.get("https://api.github.com/user").mock(
        return_value=httpx.Response(200, json=USER_RESPONSE)
    )


def mock_pr_metadata(owner: str = "ethiyor", repo: str = "patchproof", pr: int = 42) -> None:
    respx.get(f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr}").mock(
        return_value=httpx.Response(200, json=PR_METADATA_RESPONSE)
    )


def mock_pr_diff(owner: str = "ethiyor", repo: str = "patchproof", pr: int = 42) -> None:
    respx.get(f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr}").mock(
        return_value=httpx.Response(200, text=PR_DIFF_RESPONSE)
    )


def mock_issue(owner: str = "ethiyor", repo: str = "patchproof", issue: int = 10) -> None:
    respx.get(f"https://api.github.com/repos/{owner}/{repo}/issues/{issue}").mock(
        return_value=httpx.Response(200, json=ISSUE_RESPONSE)
    )


def mock_401(path: str = "/user") -> None:
    respx.get(f"https://api.github.com{path}").mock(
        return_value=httpx.Response(401, json={"message": "Bad credentials"})
    )


def mock_404(path: str) -> None:
    respx.get(f"https://api.github.com{path}").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )


def mock_rate_limit(path: str = "/user") -> None:
    respx.get(f"https://api.github.com{path}").mock(
        return_value=httpx.Response(403, json={"message": "API rate limit exceeded"})
    )
