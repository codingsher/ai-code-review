"""POST review results to the API's internal callback."""
import logging
import os

import httpx

logger = logging.getLogger("reporter")

API_URL = os.getenv("API_INTERNAL_URL", "http://api:8000")
INTERNAL_SECRET = os.getenv("INTERNAL_API_SECRET", "dev-internal-secret")


async def report_result(job_id: str, result: dict) -> None:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{API_URL}/api/internal/reviews/{job_id}/result",
                json=result,
                headers={"X-Internal-Secret": INTERNAL_SECRET},
            )
            resp.raise_for_status()
    except Exception:
        logger.exception("Failed to report result for job %s", job_id)
