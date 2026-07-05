from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from llm.client import call_llm
from tests.mocks.llm_responses import STEP1_REQUIREMENTS


# ---------------------------------------------------------------------------
# Helper: build a mock OpenAI response object
# ---------------------------------------------------------------------------

def _mock_response(content: dict) -> MagicMock:
    """Return a mock that looks like an openai.types.chat.ChatCompletion."""
    msg = MagicMock()
    msg.content = json.dumps(content)

    choice = MagicMock()
    choice.message = msg

    usage = MagicMock()
    usage.prompt_tokens = 100
    usage.completion_tokens = 50
    usage.total_tokens = 150

    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage
    return resp


def _bad_response() -> MagicMock:
    """Return a mock whose content is not valid JSON."""
    msg = MagicMock()
    msg.content = "{ not : valid json {{{"

    choice = MagicMock()
    choice.message = msg

    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = None
    return resp


# ---------------------------------------------------------------------------
# Missing API key
# ---------------------------------------------------------------------------

class TestMissingApiKey:
    def test_raises_when_key_not_set(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            call_llm([{"role": "user", "content": "hello"}])

    def test_error_message_is_helpful(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(RuntimeError) as exc_info:
            call_llm([{"role": "user", "content": "hello"}])
        assert ".env" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Successful call
# ---------------------------------------------------------------------------

class TestSuccessfulCall:
    def test_returns_parsed_dict(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234")
        with patch("llm.client.OpenAI") as mock_openai:
            mock_openai.return_value.chat.completions.create.return_value = (
                _mock_response(STEP1_REQUIREMENTS)
            )
            result = call_llm([{"role": "user", "content": "extract requirements"}])
        assert result == STEP1_REQUIREMENTS

    def test_json_mode_is_set(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234")
        with patch("llm.client.OpenAI") as mock_openai:
            mock_create = mock_openai.return_value.chat.completions.create
            mock_create.return_value = _mock_response({"key": "value"})
            call_llm([{"role": "user", "content": "test"}])
            _, kwargs = mock_create.call_args
            assert kwargs["response_format"] == {"type": "json_object"}

    def test_temperature_is_01(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234")
        with patch("llm.client.OpenAI") as mock_openai:
            mock_create = mock_openai.return_value.chat.completions.create
            mock_create.return_value = _mock_response({"key": "value"})
            call_llm([{"role": "user", "content": "test"}])
            _, kwargs = mock_create.call_args
            assert kwargs["temperature"] == 0.1

    def test_default_model_is_gpt4o(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234")
        with patch("llm.client.OpenAI") as mock_openai:
            mock_create = mock_openai.return_value.chat.completions.create
            mock_create.return_value = _mock_response({"k": "v"})
            call_llm([{"role": "user", "content": "test"}])
            _, kwargs = mock_create.call_args
            assert kwargs["model"] == "gpt-4o"

    def test_custom_model_is_passed(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234")
        with patch("llm.client.OpenAI") as mock_openai:
            mock_create = mock_openai.return_value.chat.completions.create
            mock_create.return_value = _mock_response({"k": "v"})
            call_llm([{"role": "user", "content": "test"}], model="gpt-4o-mini")
            _, kwargs = mock_create.call_args
            assert kwargs["model"] == "gpt-4o-mini"

    def test_messages_are_forwarded(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234")
        msgs = [{"role": "system", "content": "You are helpful."}, {"role": "user", "content": "hi"}]
        with patch("llm.client.OpenAI") as mock_openai:
            mock_create = mock_openai.return_value.chat.completions.create
            mock_create.return_value = _mock_response({"k": "v"})
            call_llm(msgs)
            _, kwargs = mock_create.call_args
            assert kwargs["messages"] == msgs


# ---------------------------------------------------------------------------
# Retry behaviour
# ---------------------------------------------------------------------------

class TestRetry:
    def test_retries_on_connection_error(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234")
        from openai import APIConnectionError

        with patch("llm.client.OpenAI") as mock_openai, \
             patch("llm.client.time.sleep"):
            mock_create = mock_openai.return_value.chat.completions.create
            mock_create.side_effect = [
                APIConnectionError(request=MagicMock()),
                _mock_response({"result": "ok"}),
            ]
            result = call_llm([{"role": "user", "content": "test"}])
            assert result == {"result": "ok"}
            assert mock_create.call_count == 2

    def test_retries_on_rate_limit(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234")
        from openai import RateLimitError

        with patch("llm.client.OpenAI") as mock_openai, \
             patch("llm.client.time.sleep"):
            mock_create = mock_openai.return_value.chat.completions.create
            mock_create.side_effect = [
                RateLimitError(message="rate limit", response=MagicMock(), body={}),
                _mock_response({"result": "ok"}),
            ]
            result = call_llm([{"role": "user", "content": "test"}])
            assert result == {"result": "ok"}
            assert mock_create.call_count == 2

    def test_retries_on_invalid_json(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234")
        with patch("llm.client.OpenAI") as mock_openai, \
             patch("llm.client.time.sleep"):
            mock_create = mock_openai.return_value.chat.completions.create
            mock_create.side_effect = [
                _bad_response(),
                _mock_response({"result": "ok"}),
            ]
            result = call_llm([{"role": "user", "content": "test"}])
            assert result == {"result": "ok"}
            assert mock_create.call_count == 2

    def test_raises_after_all_retries_exhausted(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234")
        from openai import APIConnectionError

        with patch("llm.client.OpenAI") as mock_openai, \
             patch("llm.client.time.sleep"):
            mock_create = mock_openai.return_value.chat.completions.create
            mock_create.side_effect = APIConnectionError(request=MagicMock())
            with pytest.raises(RuntimeError, match="failed after"):
                call_llm([{"role": "user", "content": "test"}], max_retries=2)
            assert mock_create.call_count == 2

    def test_non_retryable_api_error_raises_immediately(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234")
        from openai import AuthenticationError

        with patch("llm.client.OpenAI") as mock_openai, \
             patch("llm.client.time.sleep"):
            mock_create = mock_openai.return_value.chat.completions.create
            mock_create.side_effect = AuthenticationError(
                message="invalid key", response=MagicMock(), body={}
            )
            with pytest.raises(RuntimeError, match="not retryable"):
                call_llm([{"role": "user", "content": "test"}], max_retries=3)
            # Must not retry — should fail on first attempt
            assert mock_create.call_count == 1

    def test_sleep_is_called_between_retries(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test1234")
        from openai import APIConnectionError

        with patch("llm.client.OpenAI") as mock_openai, \
             patch("llm.client.time.sleep") as mock_sleep:
            mock_create = mock_openai.return_value.chat.completions.create
            mock_create.side_effect = [
                APIConnectionError(request=MagicMock()),
                _mock_response({"k": "v"}),
            ]
            call_llm([{"role": "user", "content": "test"}])
            mock_sleep.assert_called_once()


# ---------------------------------------------------------------------------
# Security: API key is never logged in full
# ---------------------------------------------------------------------------

class TestApiKeySecurity:
    def test_key_not_in_debug_logs(self, monkeypatch, caplog):
        import logging
        full_key = "sk-supersecretkey1234567890abcdef"
        monkeypatch.setenv("OPENAI_API_KEY", full_key)

        with patch("llm.client.OpenAI") as mock_openai, \
             caplog.at_level(logging.DEBUG, logger="llm.client"):
            mock_openai.return_value.chat.completions.create.return_value = (
                _mock_response({"k": "v"})
            )
            call_llm([{"role": "user", "content": "test"}])

        for record in caplog.records:
            assert full_key not in record.message, (
                f"Full API key found in log message: {record.message}"
            )
