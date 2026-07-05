"""Core schema: users, repos, PRs, reviews, findings, jobs."""
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    login: Mapped[str] = mapped_column(String(120))
    avatar_url: Mapped[str] = mapped_column(String(500), default="")
    role: Mapped[str] = mapped_column(String(20), default="member")  # member|admin

    repositories: Mapped[list["Repository"]] = relationship(back_populates="owner")


class Repository(Base, TimestampMixin):
    __tablename__ = "repositories"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(300), unique=True, index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    active: Mapped[bool] = mapped_column(default=True)

    owner: Mapped[User] = relationship(back_populates="repositories")
    pull_requests: Mapped[list["PullRequest"]] = relationship(back_populates="repository")


class PullRequest(Base, TimestampMixin):
    __tablename__ = "pull_requests"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("repositories.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500), default="")
    author: Mapped[str] = mapped_column(String(120), default="")

    repository: Mapped[Repository] = relationship(back_populates="pull_requests")
    reviews: Mapped[list["Review"]] = relationship(back_populates="pull_request")

    __table_args__ = (Index("ix_pr_repo_number", "repository_id", "number", unique=True),)


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    pull_request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pull_requests.id"), index=True)
    job_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    head_sha: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)  # queued|processing|done|failed|dead
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    findings_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")

    pull_request: Mapped[PullRequest] = relationship(back_populates="reviews")
    findings: Mapped[list["ReviewFinding"]] = relationship(back_populates="review")


class ReviewFinding(Base, TimestampMixin):
    __tablename__ = "review_findings"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reviews.id"), index=True)
    source: Mapped[str] = mapped_column(String(20))  # ruff|bandit|llm
    title: Mapped[str] = mapped_column(String(500))
    severity: Mapped[str] = mapped_column(String(20), index=True)
    category: Mapped[str] = mapped_column(String(30), index=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    file: Mapped[str] = mapped_column(String(500))
    line: Mapped[int] = mapped_column(Integer)
    detail: Mapped[dict] = mapped_column(JSONB, default=dict)

    review: Mapped[Review] = relationship(back_populates="findings")
