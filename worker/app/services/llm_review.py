"""LLM review engine.

Calls the configured LLM provider, validates output against FindingList schema.
Retries once on invalid JSON; drops low-confidence findings.
"""
import asyncio
import json
import logging
import os

import httpx
from pydantic import ValidationError

from app.schemas import Finding, FindingList
from app.services.prompt_builder import SYSTEM_PROMPT, build_review_prompt

logger = logging.getLogger("llm")

# Any OpenAI-compatible endpoint (Gemini, Groq, OpenRouter, Ollama) or Anthropic
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # gemini|anthropic|openai_compatible
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
API_KEY = os.getenv("LLM_API_KEY", "") or os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")
MIN_CONFIDENCE = float(os.getenv("LLM_MIN_CONFIDENCE", "0.5"))
MAX_TOKENS = 4096


async def _call_llm(prompt: str) -> str:
    last_exc: Exception | None = None
    for attempt in range(4):
        try:
            return await _call_llm_once(prompt)
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 500, 502, 503, 529):
                last_exc = e
                wait = 2 ** attempt * 5  # 5s, 10s, 20s, 40s
                logger.warning("LLM %s, retry in %ss", e.response.status_code, wait)
                await asyncio.sleep(wait)
            else:
                raise
    raise last_exc


async def _call_llm_once(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        if LLM_PROVIDER == "anthropic":
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": API_KEY, "anthropic-version": "2023-06-01"},
                json={"model": MODEL, "max_tokens": MAX_TOKENS,
                      "system": SYSTEM_PROMPT,
                      "messages": [{"role": "user", "content": prompt}]},
            )
            resp.raise_for_status()
            return "".join(b.get("text", "") for b in resp.json()["content"])
        # OpenAI-compatible (Gemini, Groq, OpenRouter, Ollama)
        resp = await client.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={"model": MODEL, "max_tokens": MAX_TOKENS,
                  "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                               {"role": "user", "content": prompt}]},
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def _parse(raw: str) -> FindingList:
    text = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return FindingList.model_validate(json.loads(text))


async def run_llm_review(
    repo_dir: str, job: dict, files: list[str], static_findings: list[dict]
) -> list[Finding]:
    if not API_KEY:
        logger.warning("LLM_API_KEY not set; skipping LLM review")
        return []

    prompt = await build_review_prompt(repo_dir, job, files, static_findings)

    raw = await _call_llm(prompt)
    try:
        result = _parse(raw)
    except (json.JSONDecodeError, ValidationError):
        logger.warning("Invalid LLM JSON, retrying once")
        raw = await _call_llm(prompt + "\n\nYour previous response was invalid JSON. Return ONLY the JSON object.")
        try:
            result = _parse(raw)
        except (json.JSONDecodeError, ValidationError):
            logger.error("LLM returned invalid JSON twice; skipping AI findings")
            return []

    kept = [f for f in result.findings if f.confidence >= MIN_CONFIDENCE]
    logger.info("LLM: %d findings, %d kept (confidence >= %s)", len(result.findings), len(kept), MIN_CONFIDENCE)
    return kept
