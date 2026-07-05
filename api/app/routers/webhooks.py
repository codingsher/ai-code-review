"""GitHub webhook receiver.

Verifies HMAC signature, filters PR events, enqueues review jobs.
Fast path only — no heavy work here.
"""
import hashlib
import hmac
import logging
import uuid

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.core.config import settings
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.services.queue import enqueue_review_job
from app.services.review_store import create_review_record

logger = logging.getLogger(__name__)
router = APIRouter()

ACTIONABLE_PR_ACTIONS = {"opened", "synchronize", "reopened"}


def verify_signature(body: bytes, signature: str | None) -> None:
    if not signature:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing signature")
    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature")


@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()
    verify_signature(body, x_hub_signature_256)

    if x_github_event == "ping":
        return {"ok": True}

    if x_github_event != "pull_request":
        return {"ok": True, "skipped": x_github_event}

    payload = await request.json()
    action = payload.get("action")
    if action not in ACTIONABLE_PR_ACTIONS:
        return {"ok": True, "skipped": action}

    pr = payload["pull_request"]
    job = {
        "job_id": str(uuid.uuid4()),
        "repo_full_name": payload["repository"]["full_name"],
        "clone_url": payload["repository"]["clone_url"],
        "pr_number": pr["number"],
        "head_sha": pr["head"]["sha"],
        "base_sha": pr["base"]["sha"],
        "installation_id": payload.get("installation", {}).get("id"),
    }
    await create_review_record(db, payload, job["job_id"])
    await enqueue_review_job(job)
    logger.info("Enqueued review job", extra={"repo": job["repo_full_name"], "pr": job["pr_number"]})
    return {"ok": True, "job_id": job["job_id"]}
