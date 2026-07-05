"""Builds context-rich prompts: diff + full changed files + project structure
+ static analysis results. Token-budgeted."""
import asyncio
from pathlib import Path

MAX_DIFF_CHARS = 40_000
MAX_FILE_CHARS = 30_000
MAX_TREE_ENTRIES = 150

SYSTEM_PROMPT = """You are a senior staff engineer performing a rigorous pull request review.

Analyze the diff and surrounding context for: bugs, logic errors, security \
vulnerabilities (injection, XSS, SSRF, path traversal, auth/authz flaws, unsafe \
deserialization, hardcoded secrets), race conditions, performance issues (N+1 \
queries, blocking I/O, inefficient algorithms), resource/memory leaks, exception \
handling gaps, dead code, SOLID violations, and maintainability problems.

Rules:
- Only report issues in the CHANGED lines or directly caused by the change.
- Do not repeat issues already listed under "Static analysis findings".
- Be precise about file and line numbers from the diff.
- Prefer few high-confidence findings over many speculative ones.
- Respond with ONLY a JSON object, no markdown fences, matching exactly:
{"findings": [{"title": str, "description": str, "severity": "critical|high|medium|low|info", "confidence": float 0-1, "category": "bug|security|performance|concurrency|maintainability|architecture|style", "explanation": str, "suggested_fix": str, "code_example": str, "file": str, "line": int}]}
If there are no issues, return {"findings": []}."""


async def _sh(*args: str, cwd: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        *args, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
    )
    out, _ = await proc.communicate()
    return out.decode(errors="replace")


def project_tree(repo_dir: str) -> str:
    entries = []
    for p in sorted(Path(repo_dir).rglob("*")):
        if len(entries) >= MAX_TREE_ENTRIES:
            break
        if ".git" in p.parts:
            continue
        entries.append(str(p.relative_to(repo_dir)) + ("/" if p.is_dir() else ""))
    return "\n".join(entries)


async def build_review_prompt(
    repo_dir: str, job: dict, files: list[str], static_findings: list[dict]
) -> str:
    diff = await _sh(
        "git", "diff", f"{job['base_sha']}...{job['head_sha']}", "--unified=5", cwd=repo_dir
    )
    diff = diff[:MAX_DIFF_CHARS]

    file_contents = []
    budget = MAX_FILE_CHARS
    for f in files:
        p = Path(repo_dir) / f
        if not p.is_file() or budget <= 0:
            continue
        try:
            text = p.read_text(errors="replace")[:budget]
        except OSError:
            continue
        budget -= len(text)
        file_contents.append(f"--- {f} ---\n{text}")

    static_summary = "\n".join(
        f"- {s['file']}:{s['line']} [{s['tool']}] {s['title']}" for s in static_findings[:50]
    ) or "(none)"

    return f"""Repository: {job['repo_full_name']}, PR #{job['pr_number']}

Project structure:
{project_tree(repo_dir)}

Static analysis findings (already reported — do NOT duplicate):
{static_summary}

Git diff (base...head, 5 lines context):
```diff
{diff}
```

Full content of changed files:
{chr(10).join(file_contents)}

Review the change and return the JSON findings object."""
