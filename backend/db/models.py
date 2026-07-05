from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Base class — all models inherit from this
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# ---------------------------------------------------------------------------
# Helper: UTC timestamp column with a server-side default
# ---------------------------------------------------------------------------

def _now_col() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )


# ---------------------------------------------------------------------------
# 1. users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


# ---------------------------------------------------------------------------
# 2. repositories
# ---------------------------------------------------------------------------

class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (
        UniqueConstraint("owner", "name", "provider", name="uq_repo_owner_name_provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"), default=uuid.uuid4,
    )
    owner: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'github'"), default="github")
    installation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"),
    )

    pull_requests: Mapped[list["PullRequest"]] = relationship(back_populates="repository")
    reviews: Mapped[list["Review"]] = relationship(back_populates="repository")

    def __repr__(self) -> str:
        return f"<Repository {self.provider}/{self.owner}/{self.name}>"


# ---------------------------------------------------------------------------
# 3. pull_requests
# ---------------------------------------------------------------------------

class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint("repository_id", "pr_number", name="uq_pr_repo_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"), default=uuid.uuid4,
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False,
    )
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    base_branch: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    head_branch: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # open | closed | merged
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"),
    )

    repository: Mapped["Repository"] = relationship(back_populates="pull_requests")
    reviews: Mapped[list["Review"]] = relationship(back_populates="pull_request")

    def __repr__(self) -> str:
        return f"<PullRequest #{self.pr_number} status={self.status!r}>"


# ---------------------------------------------------------------------------
# 4. reviews
# ---------------------------------------------------------------------------

class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"), default=uuid.uuid4,
    )
    repository_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=True,
    )
    pull_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pull_requests.id"), nullable=True,
    )
    task_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    diff_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    merge_recommendation: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    report_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"),
    )

    repository: Mapped[Optional["Repository"]] = relationship(back_populates="reviews")
    pull_request: Mapped[Optional["PullRequest"]] = relationship(back_populates="reviews")
    findings: Mapped[list["ReviewFinding"]] = relationship(back_populates="review", cascade="all, delete-orphan")
    requirement_checks: Mapped[list["RequirementCheck"]] = relationship(back_populates="review", cascade="all, delete-orphan")
    changed_files: Mapped[list["ChangedFile"]] = relationship(back_populates="review", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Review id={self.id} risk={self.risk_level} rec={self.merge_recommendation!r}>"


# ---------------------------------------------------------------------------
# 5. review_findings
# ---------------------------------------------------------------------------

class ReviewFinding(Base):
    __tablename__ = "review_findings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"), default=uuid.uuid4,
    )
    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False,
    )
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    line_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    line_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"),
    )

    review: Mapped["Review"] = relationship(back_populates="findings")

    def __repr__(self) -> str:
        return f"<ReviewFinding {self.category}/{self.severity} {self.title!r}>"


# ---------------------------------------------------------------------------
# 6. requirement_checks
# ---------------------------------------------------------------------------

class RequirementCheck(Base):
    __tablename__ = "requirement_checks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"), default=uuid.uuid4,
    )
    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False,
    )
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"),
    )

    review: Mapped["Review"] = relationship(back_populates="requirement_checks")

    def __repr__(self) -> str:
        return f"<RequirementCheck {self.status!r} {self.requirement_text[:40]!r}>"


# ---------------------------------------------------------------------------
# 7. changed_files
# ---------------------------------------------------------------------------

class ChangedFile(Base):
    __tablename__ = "changed_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"), default=uuid.uuid4,
    )
    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False,
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    additions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"), default=0)
    deletions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"), default=0)
    risk_flags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)

    review: Mapped["Review"] = relationship(back_populates="changed_files")

    def __repr__(self) -> str:
        return f"<ChangedFile {self.file_path!r} {self.status} +{self.additions}-{self.deletions}>"
