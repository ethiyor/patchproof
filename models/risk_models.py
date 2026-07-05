from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

RiskLevel = Literal["low", "medium", "high", "critical"]


class RiskScore(BaseModel):
    """The result of running the rule-based risk scorer on a parsed diff."""

    score: int
    level: RiskLevel
    reasons: list[str]

    def __str__(self) -> str:
        return f"{self.score} ({self.level.capitalize()})"
