"""Redis Streams job queue.

Streams (not lists) chosen for: consumer groups, at-least-once delivery,
pending-entry recovery (worker crash -> XAUTOCLAIM), and built-in job IDs.
"""
import json

import redis.asyncio as redis

from app.core.config import settings

STREAM = "review_jobs"
DLQ_STREAM = "review_jobs_dlq"

_pool: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.from_url(settings.redis_url, decode_responses=True)
    return _pool


async def enqueue_review_job(job: dict) -> str:
    r = get_redis()
    msg_id = await r.xadd(STREAM, {"payload": json.dumps(job)})
    await r.hset(f"job:{job['job_id']}", mapping={"status": "queued", "stream_id": msg_id})
    return msg_id


async def get_job_status(job_id: str) -> dict:
    r = get_redis()
    return await r.hgetall(f"job:{job_id}")
