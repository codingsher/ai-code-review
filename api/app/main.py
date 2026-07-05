"""AI Code Review Platform — API service entrypoint."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.metrics import instrument
from app.routers import auth, health, internal, repositories, reviews, webhooks

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Code Review Platform",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(repositories.router, prefix="/api/repositories", tags=["repositories"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["reviews"])
app.include_router(internal.router, prefix="/api", tags=["internal"])

instrument(app)
