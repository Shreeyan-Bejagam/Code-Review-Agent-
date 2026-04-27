

from __future__ import annotations

from app.config import get_settings
from app.github.client import GitHubClient
from app.models.schemas import ReviewResult


class CommentPoster:


    def __init__(self, github_client: GitHubClient | None = None) -> None:


        self.settings = get_settings()
        self.github_client = github_client or GitHubClient()

    async def post_review(
        self,
        repo_full_name: str,
        pr_number: int,
        installation_id: int,
        review_result: ReviewResult,
    ) -> dict:


        comments = [
            {"path": c.path, "line": c.line, "side": c.side, "body": c.body}
            for c in review_result.inline_comments[: self.settings.max_inline_comments]
        ]
        return await self.github_client.create_review(
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            installation_id=installation_id,
            body=review_result.summary,
            comments=comments or None,
        )
