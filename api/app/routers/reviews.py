"""Review history endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.security import get_current_user_id
from app.models.models import PullRequest, Repository, Review
from app.services.queue import get_job_status

router = APIRouter()


@router.get("")
async def list_reviews(
    limit: int = 20, offset: int = 0,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Review, PullRequest, Repository)
            .join(PullRequest, Review.pull_request_id == PullRequest.id)
            .join(Repository, PullRequest.repository_id == Repository.id)
            .order_by(Review.created_at.desc())
            .limit(min(limit, 100)).offset(offset)
        )
    ).all()
    return {
        "reviews": [
            {
                "id": str(r.id), "job_id": r.job_id, "status": r.status,
                "findings_count": r.findings_count, "duration_ms": r.duration_ms,
                "repo": repo.full_name, "pr_number": pr.number, "pr_title": pr.title,
                "created_at": r.created_at.isoformat(),
            }
            for r, pr, repo in rows
        ]
    }


@router.get("/{review_id}")
async def review_detail(
    review_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    review = (
        await db.execute(
            select(Review).where(Review.id == review_id).options(selectinload(Review.findings))
        )
    ).scalar_one_or_none()
    if not review:
        raise HTTPException(404, "Review not found")
    return {
        "id": str(review.id), "job_id": review.job_id, "status": review.status,
        "head_sha": review.head_sha, "duration_ms": review.duration_ms,
        "findings": [
            {
                "source": f.source, "title": f.title, "severity": f.severity,
                "category": f.category, "confidence": f.confidence,
                "file": f.file, "line": f.line, "detail": f.detail,
            }
            for f in review.findings
        ],
    }


@router.get("/jobs/{job_id}")
async def job_status(job_id: str, user_id: str = Depends(get_current_user_id)):
    status = await get_job_status(job_id)
    if not status:
        raise HTTPException(404, "Job not found")
    return status
