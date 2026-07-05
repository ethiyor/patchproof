from __future__ import annotations

import pytest
import respx
import httpx

from cli.github_client import GitHubClient, make_github_client, parse_pr_url
from models.github_models import PRMetadata
from tests.mocks.github_api import (
    USER_RESPONSE,
    PR_METADATA_RESPONSE,
    ISSUE_RESPONSE,
    mock_get_user,
    mock_pr_metadata,
    mock_issue,
    mock_401,
    mock_404,
    mock_rate_limit,
)


# ---------------------------------------------------------------------------
# make_github_client — factory
# ---------------------------------------------------------------------------

class TestMakeGitHubClient:
    def test_raises_when_token_missing(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
            make_github_client()

    def test_error_message_mentions_env_file(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        with pytest.raises(RuntimeError) as exc_info:
            make_github_client()
        assert ".env" in str(exc_info.value)

    def test_returns_client_when_token_set(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_fake1234")
        client = make_github_client()
        assert isinstance(client, GitHubClient)

    def test_token_not_logged_in_full(self, monkeypatch, caplog):
        import logging
        full_token = "ghp_supersecrettoken1234567890abcdef"
        monkeypatch.setenv("GITHUB_TOKEN", full_token)
        with caplog.at_level(logging.DEBUG, logger="cli.github_client"):
            make_github_client()
        for record in caplog.records:
            assert full_token not in record.message


# ---------------------------------------------------------------------------
# GitHubClient.get — JSON endpoint
# ---------------------------------------------------------------------------

class TestGitHubClientGet:
    @respx.mock
    def test_returns_parsed_json(self):
        mock_get_user()
        client = GitHubClient("ghp_fake1234")
        result = client.get("/user")
        assert result == USER_RESPONSE

    @respx.mock
    def test_sends_authorization_header(self):
        token = "ghp_fake1234"
        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(200, json=USER_RESPONSE)
        )
        client = GitHubClient(token)
        client.get("/user")
        request = respx.calls.last.request
        assert request.headers["authorization"] == f"Bearer {token}"

    @respx.mock
    def test_sends_accept_header(self):
        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(200, json=USER_RESPONSE)
        )
        client = GitHubClient("ghp_fake")
        client.get("/user")
        request = respx.calls.last.request
        assert "github" in request.headers["accept"]

    @respx.mock
    def test_sends_api_version_header(self):
        respx.get("https://api.github.com/user").mock(
            return_value=httpx.Response(200, json=USER_RESPONSE)
        )
        client = GitHubClient("ghp_fake")
        client.get("/user")
        request = respx.calls.last.request
        assert request.headers["x-github-api-version"] == "2022-11-28"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestGitHubClientErrors:
    @respx.mock
    def test_401_raises_with_clear_message(self):
        mock_401("/user")
        client = GitHubClient("ghp_bad_token")
        with pytest.raises(RuntimeError, match="invalid or expired"):
            client.get("/user")

    @respx.mock
    def test_403_raises_with_clear_message(self):
        mock_rate_limit("/user")
        client = GitHubClient("ghp_fake")
        with pytest.raises(RuntimeError, match="rate limit"):
            client.get("/user")

    @respx.mock
    def test_404_raises_with_path_in_message(self):
        mock_404("/repos/nonexistent/repo/pulls/1")
        client = GitHubClient("ghp_fake")
        with pytest.raises(RuntimeError, match="not found"):
            client.get("/repos/nonexistent/repo/pulls/1")


# ---------------------------------------------------------------------------
# get_raw / get_diff
# ---------------------------------------------------------------------------

class TestGitHubClientRaw:
    @respx.mock
    def test_get_raw_returns_text(self):
        respx.get("https://api.github.com/repos/owner/repo/pulls/1").mock(
            return_value=httpx.Response(200, text="diff --git a/x b/x\n+line")
        )
        client = GitHubClient("ghp_fake")
        result = client.get_raw("/repos/owner/repo/pulls/1", accept="application/vnd.github.diff")
        assert result.startswith("diff --git")

    @respx.mock
    def test_get_diff_sends_diff_accept_header(self):
        respx.get("https://api.github.com/repos/owner/repo/pulls/1").mock(
            return_value=httpx.Response(200, text="diff content")
        )
        client = GitHubClient("ghp_fake")
        client.get_diff("/repos/owner/repo/pulls/1")
        request = respx.calls.last.request
        assert request.headers["accept"] == "application/vnd.github.diff"


# ---------------------------------------------------------------------------
# parse_pr_url
# ---------------------------------------------------------------------------

class TestParsePrUrl:
    def test_valid_url_returns_tuple(self):
        owner, repo, number = parse_pr_url("https://github.com/ethiyor/patchproof/pull/42")
        assert owner == "ethiyor"
        assert repo == "patchproof"
        assert number == 42

    def test_trailing_slash_accepted(self):
        owner, repo, number = parse_pr_url("https://github.com/ethiyor/patchproof/pull/1/")
        assert number == 1

    def test_pr_number_is_int(self):
        _, _, number = parse_pr_url("https://github.com/a/b/pull/99")
        assert isinstance(number, int)

    def test_invalid_url_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid GitHub PR URL"):
            parse_pr_url("https://github.com/user/repo")

    def test_non_github_url_raises(self):
        with pytest.raises(ValueError):
            parse_pr_url("https://gitlab.com/user/repo/merge_requests/1")

    def test_missing_pr_number_raises(self):
        with pytest.raises(ValueError):
            parse_pr_url("https://github.com/user/repo/pull/")

    def test_error_message_shows_expected_format(self):
        with pytest.raises(ValueError) as exc_info:
            parse_pr_url("not-a-url")
        assert "github.com/owner/repo/pull" in str(exc_info.value)


# ---------------------------------------------------------------------------
# fetch_pr_metadata
# ---------------------------------------------------------------------------

class TestFetchPrMetadata:
    @respx.mock
    def test_returns_pr_metadata_model(self):
        mock_pr_metadata()
        mock_issue()
        client = GitHubClient("ghp_fake")
        result = client.fetch_pr_metadata("ethiyor", "patchproof", 42)
        assert isinstance(result, PRMetadata)

    @respx.mock
    def test_title_is_populated(self):
        mock_pr_metadata()
        mock_issue()
        client = GitHubClient("ghp_fake")
        result = client.fetch_pr_metadata("ethiyor", "patchproof", 42)
        assert result.title == PR_METADATA_RESPONSE["title"]

    @respx.mock
    def test_author_is_extracted(self):
        mock_pr_metadata()
        mock_issue()
        client = GitHubClient("ghp_fake")
        result = client.fetch_pr_metadata("ethiyor", "patchproof", 42)
        assert result.author == "ethiyor"

    @respx.mock
    def test_branches_are_extracted(self):
        mock_pr_metadata()
        mock_issue()
        client = GitHubClient("ghp_fake")
        result = client.fetch_pr_metadata("ethiyor", "patchproof", 42)
        assert result.base_branch == "main"
        assert result.head_branch == "feat/pdf-upload"

    @respx.mock
    def test_owner_repo_pr_number_on_model(self):
        mock_pr_metadata()
        mock_issue()
        client = GitHubClient("ghp_fake")
        result = client.fetch_pr_metadata("ethiyor", "patchproof", 42)
        assert result.owner == "ethiyor"
        assert result.repo == "patchproof"
        assert result.pr_number == 42

    @respx.mock
    def test_linked_issue_body_fetched_when_closes_keyword_present(self):
        mock_pr_metadata()   # PR body contains "Closes #10"
        mock_issue()         # issue #10 response
        client = GitHubClient("ghp_fake")
        result = client.fetch_pr_metadata("ethiyor", "patchproof", 42)
        assert result.linked_issue_body == ISSUE_RESPONSE["body"]

    @respx.mock
    def test_linked_issue_body_is_none_when_no_closes_keyword(self):
        # PR body with no Closes/Fixes keyword
        no_closes = {**PR_METADATA_RESPONSE, "body": "Just a description, no issue ref."}
        respx.get("https://api.github.com/repos/ethiyor/patchproof/pulls/42").mock(
            return_value=httpx.Response(200, json=no_closes)
        )
        client = GitHubClient("ghp_fake")
        result = client.fetch_pr_metadata("ethiyor", "patchproof", 42)
        assert result.linked_issue_body is None

    @respx.mock
    def test_linked_issue_fetch_failure_is_silent(self):
        mock_pr_metadata()  # PR body contains "Closes #10"
        # Issue fetch returns 404
        respx.get("https://api.github.com/repos/ethiyor/patchproof/issues/10").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"})
        )
        client = GitHubClient("ghp_fake")
        # Should not raise — linked_issue_body just stays None
        result = client.fetch_pr_metadata("ethiyor", "patchproof", 42)
        assert result.linked_issue_body is None
