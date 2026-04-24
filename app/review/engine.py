"""Main orchestrator for AI + SAST pull request review."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Finding as FindingORM
from app.db.models import Repo, Review
from app.github.comment_poster import CommentPoster
from app.github.diff_parser import parse_unified_diff
from app.models.schemas import Finding, ReviewResult, ReviewStatus, Severity
from app.review.llm import LLMReviewer
from app.review.prompt import build_review_prompt
from app.review.sast import run_semgrep


class ReviewEngine:
    """Coordinates diff parsing, analyzers, persistence, and comment posting."""

    def __init__(self, llm: LLMReviewer | None = None, poster: CommentPoster | None = None) -> None:
        """Initialize engine dependencies."""

        self.llm = llm or LLMReviewer()
        self.poster = poster or CommentPoster()

    async def run_review(
        self,
        session: AsyncSession,
        review_id: str,
        repo_full_name: str,
        pr_number: int,
        installation_id: int,
        diff_text: str,
    ) -> ReviewResult:
        """Execute full review pipeline and post GitHub comments."""

        review = await session.get(Review, review_id)
        if review is None:
            raise ValueError(f"Review '{review_id}' not found")

        review.status = ReviewStatus.running.value
        await session.commit()

        parsed = parse_unified_diff(diff_text)
        llm_result = await self.llm.review_diff(build_review_prompt(parsed))
        semgrep_result = await run_semgrep(parsed)

        semgrep_findings = [
            Finding(
                rule_id=item.check_id,
                title=f"Semgrep: {item.check_id}",
                description=item.message,
                severity=Severity(item.severity),
                file_path=item.path,
                line=item.line,
                suggestion=None,
                source="semgrep",
            )
            for item in semgrep_result
        ]
        findings = llm_result.findings + semgrep_findings
        summary = llm_result.summary
        if semgrep_result and not llm_result.findings and "Semgrep-only" in llm_result.summary:
            summary = f"{llm_result.summary} Found {len(semgrep_result)} Semgrep issue(s)."

        merged = ReviewResult(
            summary=summary,
            findings=findings,
            inline_comments=llm_result.inline_comments,
            metadata={"semgrep_count": len(semgrep_result)},
        )

        await self._persist_findings(session, review, findings, merged.summary)
        await self.poster.post_review(repo_full_name, pr_number, installation_id, merged)
        return merged

    async def _persist_findings(
        self, session: AsyncSession, review: Review, findings: list[Finding], summary: str
    ) -> None:
        """Store findings in database and mark review complete."""

        review.summary = summary
        review.status = ReviewStatus.completed.value
        for finding in findings:
            session.add(
                FindingORM(
                    review_id=review.id,
                    source=finding.source,
                    rule_id=finding.rule_id,
                    title=finding.title,
                    severity=finding.severity.value,
                    file_path=finding.file_path,
                    line=finding.line,
                    description=finding.description,
                    suggestion=finding.suggestion,
                )
            )
        await session.commit()

    async def ensure_repo_and_review(
        self,
        session: AsyncSession,
        repo_full_name: str,
        installation_id: int,
        pr_number: int,
        head_sha: str,
    ) -> Review:
        """Create or fetch repo and create a queued review row."""

        result = await session.execute(select(Repo).where(Repo.full_name == repo_full_name))
        repo = result.scalar_one_or_none()
        if repo is None:
            repo = Repo(full_name=repo_full_name, installation_id=installation_id)
            session.add(repo)
            await session.flush()

        review = Review(
            repo_id=repo.id,
            pr_number=pr_number,
            head_sha=head_sha,
            status=ReviewStatus.queued.value,
        )
        session.add(review)
        await session.commit()
        await session.refresh(review)
        return review
