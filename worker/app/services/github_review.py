"""Publish findings as a single PR review with inline comments.

Uses POST /repos/{repo}/pulls/{n}/reviews so all inline comments land
atomically. Findings whose file/line aren't in the diff fall back to the
review body.
"""
import logging
import os

import httpx

from app.schemas import Finding

logger = logging.getLogger("github")

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

SEV_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def _inline_body(f: Finding) -> str:
    parts = [
        f"{SEV_EMOJI[f.severity.value]} **{f.title}** ({f.severity.value}, {f.category.value}, confidence {f.confidence:.0%})",
        "",
        f.description,
        "",
        f"**Fix:** {f.suggested_fix}",
    ]
    if f.code_example:
        parts += ["", "```suggestion-context", f.code_example, "```"]
    return "\n".join(parts)


async def _diff_positions(client: httpx.AsyncClient, repo: str, pr: int) -> dict[str, set[int]]:
    """Map file -> set of new-side line numbers present in the diff."""
    resp = await client.get(f"{GITHUB_API}/repos/{repo}/pulls/{pr}/files", headers=_headers())
    resp.raise_for_status()
    positions: dict[str, set[int]] = {}
    for f in resp.json():
        lines: set[int] = set()
        new_line = 0
        for row in (f.get("patch") or "").splitlines():
            if row.startswith("@@"):
                # @@ -a,b +c,d @@
                new_line = int(row.split("+")[1].split(",")[0].split(" ")[0])
            elif row.startswith("+"):
                lines.add(new_line)
                new_line += 1
            elif not row.startswith("-"):
                new_line += 1
        positions[f["filename"]] = lines
    return positions


async def post_review(job: dict, ai_findings: list[Finding], static_report: str) -> None:
    if not GITHUB_TOKEN:
        logger.warning("No GITHUB_TOKEN; skipping review for PR #%s", job["pr_number"])
        return

    repo, pr = job["repo_full_name"], job["pr_number"]
    async with httpx.AsyncClient(timeout=30) as client:
        positions = await _diff_positions(client, repo, pr)

        comments, fallback = [], []
        for f in ai_findings:
            if f.line in positions.get(f.file, set()):
                comments.append(
                    {"path": f.file, "line": f.line, "side": "RIGHT", "body": _inline_body(f)}
                )
            else:
                fallback.append(f)

        body_lines = ["## 🤖 AI Code Review", ""]
        if fallback:
            body_lines.append("### Findings outside the diff")
            for f in fallback:
                body_lines.append(f"- {SEV_EMOJI[f.severity.value]} **{f.file}:{f.line}** — {f.title}: {f.suggested_fix}")
            body_lines.append("")
        if static_report:
            body_lines.append(static_report)
        if not comments and not fallback and not static_report:
            body_lines.append("✅ No issues found.")

        resp = await client.post(
            f"{GITHUB_API}/repos/{repo}/pulls/{pr}/reviews",
            headers=_headers(),
            json={
                "commit_id": job["head_sha"],
                "event": "COMMENT",
                "body": "\n".join(body_lines),
                "comments": comments,
            },
        )
        resp.raise_for_status()
        logger.info("Posted review: %d inline, %d fallback", len(comments), len(fallback))
