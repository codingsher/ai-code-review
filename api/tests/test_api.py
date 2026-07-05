import hashlib
import hmac

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_healthz():
    assert client.get("/healthz").json() == {"status": "ok"}


def test_reviews_requires_auth():
    assert client.get("/api/reviews").status_code == 401


def test_webhook_rejects_bad_signature():
    r = client.post(
        "/api/webhooks/github",
        content=b"{}",
        headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": "sha256=bad"},
    )
    assert r.status_code == 401


def test_webhook_ping_with_valid_signature():
    body = b"{}"
    sig = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    r = client.post(
        "/api/webhooks/github",
        content=body,
        headers={"X-GitHub-Event": "ping", "X-Hub-Signature-256": sig},
    )
    assert r.status_code == 200


def test_internal_callback_requires_secret():
    assert client.post("/api/internal/reviews/x/result", json={}).status_code == 401
