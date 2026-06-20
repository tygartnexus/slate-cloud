"""FastAPI application entry point.

Run with::

    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.account import router as account_router
from app.routes.billing import router as billing_router
from app.routes.readiness import router as readiness_router
from app.routes.verdicts import router as verdicts_router
from app.routes.webhooks import router as webhooks_router

settings = get_settings()

app = FastAPI(
    title="Slate Cloud API",
    version="0.1.0",
    description="Backend for the free Slate verdict dashboard.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(verdicts_router)
app.include_router(billing_router)
app.include_router(account_router)
app.include_router(webhooks_router)
app.include_router(readiness_router)
