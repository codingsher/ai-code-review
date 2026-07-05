"""GitHub REST client for posting review comments."""
import logging
import os

import httpx

logger = logging.getLogger("github")

GITHUB_API = "https://api.github.com"
# Phase 1: personal access token. Phase 2: GitHub App installation tokens.
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


async def post_pr_comment(job: dict, body: str) -> None:
    if not GITHUB_TOKEN:
        logger.warning("No GITHUB_TOKEN set; skipping comment for PR #%s", job["pr_number"])
        return
    url = f"{GITHUB_API}/repos/{job['repo_full_name']}/issues/{job['pr_number']}/comments"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json={"body": body},
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
        )
        resp.raise_for_status()
