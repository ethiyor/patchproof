from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import httpx

from backend.db.models import Repository, Review
from backend.db.session import get_db_session
from backend.main import app


class _ScalarRows:
    def __init__(self, rows: list[Review]):
        self._rows = rows

    def all(self) -> list[Review]:
        return self._rows


class _RowsResult:
    def __init__(self, rows: list[Review]):
        self._rows = rows

    def scalars(self) -> _ScalarRows:
        return _ScalarRows(self._rows)


class _CountResult:
    def __init__(self, total: int):
        self._total = total

    def scalar_one(self) -> int:
        return self._total


def _review(*, index: int, risk_level: str, created_at: datetime) -> Review:
    repository = Repository(
        id=uuid.uuid4(),
        owner="ethiyor",
        name=f"patchproof-{index}",
        provider="github",
    )
    review = Review(
        id=uuid.uuid4(),
        repository_id=repository.id,
        risk_score=index,
        risk_level=risk_level,
        merge_recommendation="needs_changes" if risk_level == "high" else "ready",
    )
    review.created_at = created_at
    review.repository = repository
    return review


def _override_db(mock_session: MagicMock) -> None:
    async def _mock_get_db():
        yield mock_session

    app.dependency_overrides[get_db_session] = _mock_get_db


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


async def _get_reviews(mock_session: MagicMock, path: str = "/reviews") -> httpx.Response:
    _override_db(mock_session)
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get(path)
    finally:
        _clear_overrides()


def test_get_reviews_returns_paginated_review_rows():
    now = datetime(2026, 7, 9, 12, 0, tzinfo=UTC)
    rows = [
        _review(index=9, risk_level="high", created_at=now),
        _review(index=4, risk_level="medium", created_at=now - timedelta(minutes=5)),
    ]
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(side_effect=[_CountResult(7), _RowsResult(rows)])

    response = asyncio.run(_get_reviews(mock_session, "/reviews?page=1&limit=2"))

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 7
    assert len(data["reviews"]) == 2
    assert data["reviews"][0] == {
        "review_id": str(rows[0].id),
        "repo_name": "ethiyor/patchproof-9",
        "risk_score": 9,
        "risk_level": "high",
        "merge_recommendation": "needs_changes",
        "created_at": rows[0].created_at.isoformat().replace("+00:00", "Z"),
    }
    assert data["reviews"][1]["repo_name"] == "ethiyor/patchproof-4"
    assert mock_session.execute.await_count == 2


def test_get_reviews_accepts_risk_level_filter():
    now = datetime(2026, 7, 9, 12, 0, tzinfo=UTC)
    rows = [_review(index=5, risk_level="high", created_at=now)]
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(side_effect=[_CountResult(1), _RowsResult(rows)])

    response = asyncio.run(_get_reviews(mock_session, "/reviews?page=2&limit=10&risk_level=high"))

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["reviews"][0]["risk_level"] == "high"
    executed_sql = [str(call.args[0]) for call in mock_session.execute.await_args_list]
    assert all("reviews.risk_level" in statement for statement in executed_sql)
    assert "LIMIT" in executed_sql[1]
    assert "OFFSET" in executed_sql[1]


def test_get_reviews_unknown_repository_returns_unknown_repo_name():
    now = datetime(2026, 7, 9, 12, 0, tzinfo=UTC)
    review = Review(
        id=uuid.uuid4(),
        risk_score=1,
        risk_level="low",
        merge_recommendation="ready",
    )
    review.created_at = now
    review.repository = None
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(side_effect=[_CountResult(1), _RowsResult([review])])

    response = asyncio.run(_get_reviews(mock_session))

    assert response.status_code == 200
    assert response.json()["reviews"][0]["repo_name"] == "unknown"


def test_get_reviews_rejects_invalid_pagination():
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()

    response = asyncio.run(_get_reviews(mock_session, "/reviews?page=0&limit=20"))

    assert response.status_code == 422
    mock_session.execute.assert_not_awaited()


def test_vite_dev_origin_is_allowed_by_cors():
    async def _request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.options(
                "/reviews",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "GET",
                },
            )

    response = asyncio.run(_request())

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
