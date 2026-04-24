"""GitHub webhook endpoint for pull request events."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.database import get_db_session
from app.models.schemas import PullRequestRef, WebhookAck
from app.queue.worker import get_queue, run_review_job
from app.review.engine import ReviewEngine
from app.webhook.verifier import verify_github_signature

router = APIRouter()
settings = get_settings()


def _extract_pr(payload: dict[str, Any]) -> PullRequestRef:
    """Extract pull request reference data from webhook payload."""

    pr = payload["pull_request"]
    repository = payload["repository"]
    installation = payload["installation"]
    return PullRequestRef(
        repository_full_name=str(repository["full_name"]),
        pull_request_number=int(pr["number"]),
        head_sha=str(pr["head"]["sha"]),
        base_sha=str(pr["base"]["sha"]),
        installation_id=int(installation["id"]),
    )


async def _enqueue_review_job(review_id: str, pr: PullRequestRef) -> None:
    """Enqueue a background review job in Redis RQ."""

    queue = get_queue()
    await asyncio.to_thread(
        queue.enqueue,
        run_review_job,
        review_id,
        pr.repository_full_name,
        pr.pull_request_number,
        pr.installation_id,
        job_timeout=1200,
        result_ttl=3600,
    )


@router.post("", response_model=WebhookAck)
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(default="", alias="X-Hub-Signature-256"),
    x_github_event: str = Header(default="", alias="X-GitHub-Event"),
    session: AsyncSession = Depends(get_db_session),
) -> WebhookAck:
    """Handle GitHub pull_request webhooks and queue review jobs."""

    payload_bytes = await request.body()
    if not verify_github_signature(payload_bytes, x_hub_signature_256, settings.github_webhook_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    payload = await request.json()
    action = payload.get("action")
    if x_github_event != "pull_request" or action not in {"opened", "synchronize", "reopened"}:
        raise HTTPException(status_code=status.HTTP_202_ACCEPTED, detail="Event ignored")

    pr = _extract_pr(payload)
    engine = ReviewEngine()
    review = await engine.ensure_repo_and_review(
        session=session,
        repo_full_name=pr.repository_full_name,
        installation_id=pr.installation_id,
        pr_number=pr.pull_request_number,
        head_sha=pr.head_sha,
    )
    await _enqueue_review_job(review.id, pr)

    return WebhookAck(accepted=True, review_id=review.id, queued_at=datetime.now(timezone.utc))
