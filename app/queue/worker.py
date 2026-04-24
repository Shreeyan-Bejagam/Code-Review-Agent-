"""Redis RQ worker and async review task entrypoints."""

from __future__ import annotations

import asyncio
import logging
import platform

from redis import Redis
from rq import Queue, SimpleWorker, Worker

from app.config import get_settings
from app.db.database import SessionLocal
from app.github.client import GitHubClient
from app.review.engine import ReviewEngine

logger = logging.getLogger(__name__)
settings = get_settings()


def get_queue() -> Queue:
    """Construct and return configured RQ queue."""

    redis_conn = Redis.from_url(settings.redis_url)
    return Queue(name=settings.rq_queue_name, connection=redis_conn)


def run_review_job(
    review_id: str,
    repo_full_name: str,
    pr_number: int,
    installation_id: int,
) -> None:
    """RQ-compatible sync wrapper that executes async review pipeline."""

    asyncio.run(_run_review_job_async(review_id, repo_full_name, pr_number, installation_id))


async def _run_review_job_async(
    review_id: str,
    repo_full_name: str,
    pr_number: int,
    installation_id: int,
) -> None:
    """Fetch diff and run full review for one pull request."""

    github = GitHubClient()
    engine = ReviewEngine()
    diff_text = await github.get_pr_diff(repo_full_name, pr_number, installation_id)

    async with SessionLocal() as session:
        await engine.run_review(
            session=session,
            review_id=review_id,
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            installation_id=installation_id,
            diff_text=diff_text,
        )
    logger.info("Completed review job review_id=%s", review_id)


def main() -> None:
    """Run an RQ worker process."""

    queue = get_queue()
    # macOS can crash on forked worker children due to Objective-C runtime
    # fork-safety checks. SimpleWorker avoids fork and is stable for local dev.
    worker_cls = SimpleWorker if platform.system() == "Darwin" else Worker
    worker = worker_cls([queue], connection=queue.connection)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
