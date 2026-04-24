"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.db.database import dispose_db, init_db
from app.webhook.handler import router as webhook_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down app resources."""

    await init_db()
    try:
        yield
    finally:
        await dispose_db()


app = FastAPI(title="AI Code Reviewer", version="1.0.0", lifespan=lifespan)
app.include_router(webhook_router, prefix="/webhook", tags=["webhook"])


@app.get("/healthz", tags=["system"])
async def health_check() -> dict[str, str]:
    """Return a simple health status."""

    return {"status": "ok"}
