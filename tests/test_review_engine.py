"""Tests for review engine orchestration."""

import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models import Base
from app.review.engine import ReviewEngine


class FakeLLM:
    """Deterministic fake LLM implementation for tests."""

    async def review_diff(self, _: str):  # type: ignore[no-untyped-def]
        """Return a static no-op review result."""

        from app.models.schemas import ReviewResult

        return ReviewResult(summary="ok", findings=[], inline_comments=[])


class FakePoster:
    """No-op comment poster."""

    async def post_review(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Pretend to post and return fixed response."""

        return {"id": 1}


async def _seed_review(session: AsyncSession) -> str:
    """Insert repo and review records and return review id."""

    from app.db.models import Repo

    engine = ReviewEngine(llm=FakeLLM(), poster=FakePoster())
    review = await engine.ensure_repo_and_review(
        session=session,
        repo_full_name="owner/repo",
        installation_id=123,
        pr_number=10,
        head_sha="abc",
    )
    return review.id


@pytest.mark.asyncio
async def test_review_engine_runs_pipeline() -> None:
    """Run review pipeline with fake dependencies."""

    os.environ["GITHUB_WEBHOOK_SECRET"] = "test-secret"
    os.environ["GITHUB_APP_ID"] = "1"
    os.environ["GITHUB_PRIVATE_KEY"] = "-----BEGIN RSA PRIVATE KEY-----\nTEST\n-----END RSA PRIVATE KEY-----"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    get_settings.cache_clear()

    db_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        review_id = await _seed_review(session)
        engine = ReviewEngine(llm=FakeLLM(), poster=FakePoster())
        result = await engine.run_review(
            session=session,
            review_id=review_id,
            repo_full_name="owner/repo",
            pr_number=10,
            installation_id=123,
            diff_text="diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-print(1)\n+print(2)\n",
        )
        assert result.summary == "ok"
