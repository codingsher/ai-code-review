# AI Code Review Platform

Cloud-native platform that automatically reviews GitHub Pull Requests using static analysis + LLMs.

## Architecture (Phase 1)

```
GitHub PR event ──> API (FastAPI, HMAC-verified webhook)
                        │ XADD
                        ▼
                 Redis Streams (consumer group, DLQ, XAUTOCLAIM recovery)
                        │
                        ▼
                 Worker (stateless, horizontally scalable)
                   clone → diff → Ruff/Bandit → report → PR comment
```

## Quick start

```bash
cp .env.example .env   # fill in GitHub OAuth app + webhook secret + PAT
docker compose up --build
```

Expose the webhook locally with `ngrok http 8000`, point a GitHub webhook
(pull_request events, secret = GITHUB_WEBHOOK_SECRET) at
`https://<ngrok>/api/webhooks/github`, and open a PR.

## Design decisions

- **Redis Streams over lists/RQ**: consumer groups give at-least-once delivery,
  per-consumer pending lists, and `XAUTOCLAIM` for crash recovery — a DLQ and
  retry counter complete the reliability story without extra infra.
- **Ack-after-success**: workers only `XACK` after the full pipeline completes;
  crashes mid-job are reclaimed after 5 min idle.
- **Webhook fast path**: signature verify + enqueue only; all heavy work is async.
- **Blobless clone** (`--filter=blob:none`): fast clones of large repos.

## Roadmap

- [x] Phase 1: webhook → queue → worker → static analysis → PR comment
- [x] Phase 2: LLM review engine (context-rich prompts, structured JSON findings, inline PR reviews)
- [x] Phase 3: PostgreSQL persistence (SQLAlchemy async + Alembic), review history & metrics API, worker result callback
- [x] Phase 4: React + TypeScript dashboard (Vite, Tailwind v4, React Query, Recharts; nginx-served)
- [x] Phase 5: Kubernetes (deployments, HPA, probes, ingress, StatefulSet PG), Prometheus/Grafana, GitHub Actions CI/CD (lint→test→scan→build→deploy→smoke)
