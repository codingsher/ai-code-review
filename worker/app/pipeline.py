"""Review pipeline: clone -> diff -> static analysis -> (Phase 2: LLM) -> GitHub comment."""
import asyncio
import logging
import shutil
import tempfile
from pathlib import Path

from app.analyzers.python_analyzers import run_bandit, run_ruff
from app.services.github_review import post_review
from app.services.llm_review import run_llm_review

logger = logging.getLogger("pipeline")


async def sh(*args: str, cwd: str | None = None) -> str:
    proc = await asyncio.create_subprocess_exec(
        *args, cwd=cwd,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed: {err.decode()[:500]}")
    return out.decode()


async def changed_files(repo_dir: str, base_sha: str, head_sha: str) -> list[str]:
    out = await sh("git", "diff", "--name-only", f"{base_sha}...{head_sha}", cwd=repo_dir)
    return [f for f in out.splitlines() if f.strip()]


async def run_review_pipeline(job: dict) -> dict:
    workdir = tempfile.mkdtemp(prefix="review-")
    repo_dir = str(Path(workdir) / "repo")
    try:
        await sh("git", "clone", "--filter=blob:none", job["clone_url"], repo_dir)
        await sh("git", "checkout", job["head_sha"], cwd=repo_dir)

        files = await changed_files(repo_dir, job["base_sha"], job["head_sha"])
        py_files = [f for f in files if f.endswith(".py") and (Path(repo_dir) / f).exists()]
        logger.info("PR #%s: %d changed files, %d python", job["pr_number"], len(files), len(py_files))

        static_findings: list[dict] = []
        if py_files:
            static_findings += await run_ruff(repo_dir, py_files)
            static_findings += await run_bandit(repo_dir, py_files)

        ai_findings = await run_llm_review(repo_dir, job, files, static_findings)

        static_report = format_report(static_findings) if static_findings else ""
        if ai_findings or static_findings:
            await post_review(job, ai_findings, static_report)

        total = len(static_findings) + len(ai_findings)
        return {
            "findings_count": total,
            "static": static_findings,
            "ai": [f.model_dump() for f in ai_findings],
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def format_report(findings: list[dict]) -> str:
    by_sev = {"high": [], "medium": [], "low": []}
    for f in findings:
        by_sev.setdefault(f.get("severity", "low"), []).append(f)
    lines = ["### Static analysis", ""]
    for sev in ("high", "medium", "low"):
        if not by_sev[sev]:
            continue
        lines.append(f"### {sev.capitalize()} ({len(by_sev[sev])})")
        for f in by_sev[sev][:20]:
            lines.append(f"- **{f['file']}:{f['line']}** [{f['tool']}] {f['title']}")
        lines.append("")
    lines.append(f"*{len(findings)} total findings.*")
    return "\n".join(lines)
