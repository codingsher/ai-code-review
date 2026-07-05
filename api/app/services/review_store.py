"""Persistence for the review lifecycle.

API path: webhook -> create_review_record (repo/PR upsert + queued review).
Worker path: worker POSTs results to internal callback -> save_review_result.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import PullRequest, Repository, Review, ReviewFinding, User


async def _get_or_create_repo(db: AsyncSession, payload: dict) -> Repository:
    gh_repo = payload["repository"]
    repo = (
        await db.execute(select(Repository).where(Repository.github_id == gh_repo["id"]))
    ).scalar_one_or_none()
    if repo:
        return repo
    # owner may not exist yet (webhook before OAuth): create shadow user
    gh_owner = gh_repo["owner"]
    owner = (
        await db.execute(select(User).where(User.github_id == gh_owner["id"]))
    ).scalar_one_or_none()
    if not owner:
        owner = User(github_id=gh_owner["id"], login=gh_owner["login"],
                     avatar_url=gh_owner.get("avatar_url", ""))
        db.add(owner)
        await db.flush()
    repo = Repository(github_id=gh_repo["id"], full_name=gh_repo["full_name"], owner_id=owner.id)
    db.add(repo)
    await db.flush()
    return repo


async def create_review_record(db: AsyncSession, payload: dict, job_id: str) -> Review:
    repo = await _get_or_create_repo(db, payload)
    gh_pr = payload["pull_request"]
    pr = (
        await db.execute(
            select(PullRequest).where(
                PullRequest.repository_id == repo.id, PullRequest.number == gh_pr["number"]
            )
        )
    ).scalar_one_or_none()
    if not pr:
        pr = PullRequest(
            repository_id=repo.id, number=gh_pr["number"],
            title=gh_pr.get("title", ""), author=gh_pr["user"]["login"],
        )
        db.add(pr)
        await db.flush()
    review = Review(pull_request_id=pr.id, job_id=job_id, head_sha=gh_pr["head"]["sha"])
    db.add(review)
    await db.commit()
    return review


async def save_review_result(db: AsyncSession, job_id: str, result: dict) -> Review | None:
    review = (
        await db.execute(select(Review).where(Review.job_id == job_id))
    ).scalar_one_or_none()
    if not review:
        return None
    review.status = result["status"]
    review.duration_ms = result.get("duration_ms")
    review.findings_count = result.get("findings_count", 0)
    review.error = result.get("error", "")

    for s in result.get("static", []):
        db.add(ReviewFinding(
            review_id=review.id, source=s["tool"], title=s["title"][:500],
            severity=s["severity"], category=s["category"], file=s["file"][:500],
            line=s["line"], detail=s,
        ))
    for a in result.get("ai", []):
        db.add(ReviewFinding(
            review_id=review.id, source="llm", title=a["title"][:500],
            severity=a["severity"], category=a["category"], confidence=a["confidence"],
            file=a["file"][:500], line=a["line"], detail=a,
        ))
    await db.commit()
    return review
