"""Ruff and Bandit wrappers producing a unified finding schema."""
import asyncio
import json

SEVERITY_MAP_BANDIT = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}


async def _run(cmd: list[str], cwd: str) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=cwd,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    out, _ = await proc.communicate()
    return proc.returncode, out.decode()


async def run_ruff(repo_dir: str, files: list[str]) -> list[dict]:
    code, out = await _run(["ruff", "check", "--output-format=json", *files], repo_dir)
    if not out.strip():
        return []
    return [
        {
            "tool": "ruff",
            "file": item["filename"].removeprefix(repo_dir + "/"),
            "line": item["location"]["row"],
            "title": f"{item['code']}: {item['message']}",
            "severity": "medium" if item["code"].startswith(("F", "B")) else "low",
            "category": "lint",
        }
        for item in json.loads(out)
    ]


async def run_bandit(repo_dir: str, files: list[str]) -> list[dict]:
    code, out = await _run(["bandit", "-f", "json", *files], repo_dir)
    if not out.strip():
        return []
    data = json.loads(out)
    return [
        {
            "tool": "bandit",
            "file": item["filename"].removeprefix(repo_dir + "/"),
            "line": item["line_number"],
            "title": f"{item['test_id']}: {item['issue_text']}",
            "severity": SEVERITY_MAP_BANDIT.get(item["issue_severity"], "low"),
            "category": "security",
        }
        for item in data.get("results", [])
    ]
