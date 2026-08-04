from __future__ import annotations

from unittest.mock import Mock

import httpx
from typer.testing import CliRunner

from cli.config_loader import get_patchproof_api_url
from cli.main import app, _try_backend_review


class FakeDiffResult:
    def __init__(self, raw: str = "diff --git a/app.py b/app.py\n") -> None:
        self.raw = raw
        self.repo_name = "patchproof"
        self.branch = "main"

    def __str__(self) -> str:
        return "1 file changed (+1 -0)"


class TestPatchproofApiUrlConfig:
    def test_defaults_to_local_backend(self, monkeypatch):
        monkeypatch.delenv("PATCHPROOF_API_URL", raising=False)

        assert get_patchproof_api_url() == "http://localhost:8000"

    def test_blank_value_enables_offline_mode(self, monkeypatch):
        monkeypatch.setenv("PATCHPROOF_API_URL", "   ")

        assert get_patchproof_api_url() is None

    def test_strips_trailing_slash(self, monkeypatch):
        monkeypatch.setenv("PATCHPROOF_API_URL", "http://localhost:9000/")

        assert get_patchproof_api_url() == "http://localhost:9000"


class TestBackendReviewRequest:
    def test_writes_backend_report_and_prints_review_id(self, tmp_path, monkeypatch, capsys):
        output = tmp_path / "report.md"
        diff_result = FakeDiffResult()
        response = httpx.Response(
            200,
            json={
                "review_id": "rev_abc123",
                "report_markdown": "# Backend Report\n",
                "risk_score": 1,
                "risk_level": "low",
                "merge_recommendation": "ready",
                "status": "completed",
            },
        )
        post = Mock(return_value=response)
        monkeypatch.setattr("cli.main.httpx.post", post)

        completed = _try_backend_review(
            api_url="http://localhost:8000",
            task_text="Add a helper",
            diff_result=diff_result,
            output=output,
        )

        assert completed is True
        assert output.read_text(encoding="utf-8") == "# Backend Report\n"
        assert "Review saved: rev_abc123" in capsys.readouterr().out
        post.assert_called_once_with(
            "http://localhost:8000/reviews/local",
            json={
                "task": "Add a helper",
                "diff": "diff --git a/app.py b/app.py\n",
                "repo_name": "patchproof",
                "branch": "main",
            },
            timeout=60.0,
        )

    def test_unreachable_backend_returns_false(self, tmp_path, monkeypatch):
        output = tmp_path / "report.md"
        diff_result = FakeDiffResult()
        monkeypatch.setattr(
            "cli.main.httpx.post",
            Mock(side_effect=httpx.ConnectError("connection refused")),
        )

        completed = _try_backend_review(
            api_url="http://localhost:8000",
            task_text="Add a helper",
            diff_result=diff_result,
            output=output,
        )

        assert completed is False
        assert not output.exists()


class TestReviewCommandBackendMode:
    def test_review_command_uses_backend_when_configured(self, tmp_path, monkeypatch):
        task_file = tmp_path / "task.txt"
        diff_file = tmp_path / "change.diff"
        output_file = tmp_path / "report.md"
        task_file.write_text("Add a helper", encoding="utf-8")
        diff_file.write_text("diff --git a/app.py b/app.py\n", encoding="utf-8")
        diff_result = FakeDiffResult(diff_file.read_text(encoding="utf-8"))
        monkeypatch.setattr("cli.main.collect_diff", Mock(return_value=diff_result))
        monkeypatch.setattr("cli.main.get_patchproof_api_url", Mock(return_value="http://api.test"))
        local_report = Mock()
        monkeypatch.setattr("cli.main._write_local_review_report", local_report)

        def fake_backend_review(*, api_url, task_text, diff_result, output):
            output.write_text("# Backend Report\n", encoding="utf-8")
            return True

        backend_review = Mock(side_effect=fake_backend_review)
        monkeypatch.setattr("cli.main._try_backend_review", backend_review)

        result = CliRunner().invoke(
            app,
            [
                "review",
                "--task",
                str(task_file),
                "--diff",
                str(diff_file),
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == 0
        assert output_file.read_text(encoding="utf-8") == "# Backend Report\n"
        backend_review.assert_called_once()
        local_report.assert_not_called()