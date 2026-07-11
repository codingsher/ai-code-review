# AI Code Review Platform

A platform that reviews GitHub pull requests automatically. When a PR opens, it clones the repo, runs static analysis, sends the diff with full context to an LLM, and posts inline review comments back on the PR within seconds.

## How it works

```bash
GitHub PR event -> API (FastAPI, HMAC-verified webhook)
|
v
Redis Streams (consumer groups, DLQ, crash recovery)
|
v
Worker (stateless, horizontally scalable)
clone -> diff -> Ruff/Bandit -> LLM review -> inline PR comments
|
v
PostgreSQL -> React dashboard (history, metrics)
```

## Quick start

```bash
cp .env.example .env   # fill in GitHub OAuth app, webhook secret, PAT, LLM key
docker compose up -d --build
```

Point a GitHub webhook (pull_request events, content type application/json, secret matching GITHUB_WEBHOOK_SECRET) at:
```bash
http://<your-host>:8000/api/webhooks/github
```

For local testing, expose port 8000 with ngrok. On a server with a public IP, use the IP directly. Then open a PR with a code change and watch the review land.

Dashboard runs at port 5173. API docs at /api/docs.

## LLM provider

Any OpenAI-compatible endpoint works. Configure in .env:

```bash
LLM_PROVIDER=gemini
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_API_KEY=your-key
LLM_MODEL=gemini-2.5-flash-lite
```

Groq, OpenRouter, and Ollama work the same way with their base URLs. Anthropic is supported natively with LLM_PROVIDER=anthropic.

## Design decisions

- Redis Streams over lists or RQ: consumer groups give at-least-once delivery, per-consumer pending lists, and XAUTOCLAIM for crash recovery. A dead letter queue and retry counter complete the reliability story without extra infrastructure.
- Ack after success: workers only acknowledge a job after the full pipeline completes. If a worker dies mid-review, the job gets reclaimed and retried.
- Webhook fast path: the API only verifies the signature and enqueues. All heavy work happens asynchronously in workers.
- Blobless clones keep large repos fast to fetch.
- The LLM is skipped entirely when a PR has no reviewable files, and rate limits are handled with exponential backoff. Wasted model calls cost real quota.
- LLM output is schema validated. Findings that fail validation or fall below the confidence threshold are dropped rather than posted.

## Stack

FastAPI, Redis Streams, PostgreSQL with SQLAlchemy and Alembic, React with TypeScript and Recharts, Ruff and Bandit for static analysis, Docker Compose for local development, Kubernetes manifests with HPAs and Prometheus/Grafana for production, GitHub Actions for CI/CD.

## Running tests

```bash
cd api && pytest tests
cd worker && pytest tests
```

## Deploying to Kubernetes

Create the secret described in deploy/k8s/02-secrets.yaml, replace OWNER in the image names, then:

```bash
kubectl apply -f deploy/k8s/
```

The GitHub Actions pipeline does this automatically on push to main, given a KUBECONFIG repo secret.

