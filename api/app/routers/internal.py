"""Internal worker callback (shared-secret auth) + metrics endpoints."""
import os

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.models import PullRequest, Repository, Review, ReviewFinding
from app.services.review_store import save_review_result

router = APIRouter()

INTERNAL_SECRET = os.getenv("INTERNAL_API_SECRET", "dev-internal-secret")


def verify_internal(x_internal_secret: str = Header(None)):
    if x_internal_secret != INTERNAL_SECRET:
        raise HTTPException(401, "Invalid internal secret")


@router.post("/internal/reviews/{job_id}/result", dependencies=[Depends(verify_internal)])
async def review_result(job_id: str, result: dict, db: AsyncSession = Depends(get_db)):
    review = await save_review_result(db, job_id, result)
    if not review:
        raise HTTPException(404, "Unknown job_id")
    return {"ok": True, "review_id": str(review.id)}


@router.get("/metrics/summary")
async def metrics_summary(db: AsyncSession = Depends(get_db)):
    totals = (
        await db.execute(
            select(
                func.count(Review.id),
                func.sum(case((Review.status == "done", 1), else_=0)),
                func.sum(case((Review.status.in_(("failed", "dead")), 1), else_=0)),
                func.avg(Review.duration_ms),
            )
        )
    ).one()
    by_severity = (
        await db.execute(
            select(ReviewFinding.severity, func.count()).group_by(ReviewFinding.severity)
        )
    ).all()
    by_category = (
        await db.execute(
            select(ReviewFinding.category, func.count()).group_by(ReviewFinding.category)
        )
    ).all()
    per_repo = (
        await db.execute(
            select(Repository.full_name, func.count(Review.id))
            .join(PullRequest, PullRequest.repository_id == Repository.id)
            .join(Review, Review.pull_request_id == PullRequest.id)
            .group_by(Repository.full_name)
            .order_by(func.count(Review.id).desc())
            .limit(10)
        )
    ).all()
    total, done, failed, avg_ms = totals
    return {
        "total_reviews": total or 0,
        "success": done or 0,
        "failed": failed or 0,
        "success_rate": round((done or 0) / total, 3) if total else None,
        "avg_duration_ms": round(avg_ms) if avg_ms else None,
        "findings_by_severity": dict(by_severity),
        "findings_by_category": dict(by_category),
        "reviews_per_repository": dict(per_repo),
    }
