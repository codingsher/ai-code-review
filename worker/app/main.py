"""Review worker.

Consumes review jobs from Redis Streams via a consumer group.
At-least-once semantics: ack only after full pipeline succeeds.
Failed jobs retry up to MAX_RETRIES, then go to DLQ.
"""
import asyncio
import json
import logging
import os
import socket
import uuid

from pathlib import Path

import redis.asyncio as redis

import time

from app.pipeline import run_review_pipeline
from app.services.reporter import report_result

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("worker")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STREAM = "review_jobs"
DLQ = "review_jobs_dlq"
GROUP = "review_workers"
CONSUMER = f"{socket.gethostname()}-{uuid.uuid4().hex[:6]}"
MAX_RETRIES = 3
CLAIM_IDLE_MS = 5 * 60 * 1000  # reclaim jobs from dead workers after 5 min


async def ensure_group(r: redis.Redis) -> None:
    try:
        await r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


async def handle(r: redis.Redis, msg_id: str, fields: dict) -> None:
    job = json.loads(fields["payload"])
    job_key = f"job:{job['job_id']}"
    await r.hset(job_key, mapping={"status": "processing", "worker": CONSUMER})
    started = time.monotonic()
    try:
        result = await run_review_pipeline(job)
        duration_ms = int((time.monotonic() - started) * 1000)
        await r.hset(job_key, mapping={"status": "done", "findings": result["findings_count"]})
        await r.xack(STREAM, GROUP, msg_id)
        await report_result(job["job_id"], {"status": "done", "duration_ms": duration_ms, **result})
        logger.info("Job %s done: %s findings", job["job_id"], result["findings_count"])
    except Exception:
        logger.exception("Job %s failed", job["job_id"])
        retries = await r.hincrby(job_key, "retries", 1)
        if retries >= MAX_RETRIES:
            await r.xadd(DLQ, fields)
            await r.xack(STREAM, GROUP, msg_id)
            await r.hset(job_key, "status", "dead")
            await report_result(job["job_id"], {"status": "dead", "error": "max retries exceeded"})
            logger.error("Job %s moved to DLQ", job["job_id"])
        else:
            await r.hset(job_key, "status", "queued")
            # leave unacked; XAUTOCLAIM path or next read retries it


async def reclaim_stale(r: redis.Redis) -> None:
    """Recover jobs from crashed workers."""
    while True:
        await asyncio.sleep(60)
        try:
            _, messages, _ = await r.xautoclaim(STREAM, GROUP, CONSUMER, CLAIM_IDLE_MS, "0")
            for msg_id, fields in messages:
                await handle(r, msg_id, fields)
        except Exception:
            logger.exception("xautoclaim failed")


async def main() -> None:
    r = redis.from_url(REDIS_URL, decode_responses=True)
    await ensure_group(r)
    asyncio.create_task(reclaim_stale(r))
    logger.info("Worker %s consuming from %s", CONSUMER, STREAM)
    while True:
        Path("/tmp/heartbeat").touch()
        resp = await r.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=1, block=5000)
        for _, messages in resp or []:
            for msg_id, fields in messages:
                await handle(r, msg_id, fields)


if __name__ == "__main__":
    asyncio.run(main())
