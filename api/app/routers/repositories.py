"""Repository management."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user_id
from app.models.models import PullRequest, Repository, Review

router = APIRouter()


@router.get("")
async def list_repositories(
    user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)
):
    rows = (
        await db.execute(
            select(Repository, func.count(Review.id))
            .outerjoin(PullRequest, PullRequest.repository_id == Repository.id)
            .outerjoin(Review, Review.pull_request_id == PullRequest.id)
            .group_by(Repository.id)
            .order_by(Repository.created_at.desc())
        )
    ).all()
    return {
        "repositories": [
            {
                "id": str(repo.id), "full_name": repo.full_name,
                "active": repo.active, "review_count": count,
            }
            for repo, count in rows
        ]
    }
