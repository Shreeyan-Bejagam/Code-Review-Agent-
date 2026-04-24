"""Async GitHub API client with installation token auth."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import jwt

from app.config import get_settings


class GitHubClient:
    """GitHub API client that mints and uses installation tokens."""

    def __init__(self) -> None:
        """Initialize client settings."""

        self.settings = get_settings()

    def _build_app_jwt(self) -> str:
        """Build signed JWT for GitHub App authentication."""

        now = datetime.now(timezone.utc)
        payload = {
            "iat": int((now - timedelta(seconds=60)).timestamp()),
            "exp": int((now + timedelta(minutes=9)).timestamp()),
            "iss": self.settings.github_app_id,
        }
        return jwt.encode(payload, self.settings.github_private_key, algorithm="RS256")

    async def _request(self, method: str, url: str, headers: dict[str, str], **kwargs: Any) -> httpx.Response:
        """Perform an HTTP request with timeout handling."""

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    async def get_installation_token(self, installation_id: int) -> str:
        """Exchange app JWT for a short-lived installation token."""

        jwt_token = self._build_app_jwt()
        url = f"{self.settings.github_api_base_url}/app/installations/{installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        response = await self._request("POST", url, headers=headers)
        data = response.json()
        return str(data["token"])

    async def get_pr_diff(self, repo_full_name: str, pr_number: int, installation_id: int) -> str:
        """Fetch pull request unified diff text."""

        token = await self.get_installation_token(installation_id)
        url = f"{self.settings.github_api_base_url}/repos/{repo_full_name}/pulls/{pr_number}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3.diff",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        response = await self._request("GET", url, headers=headers)
        return response.text

    async def create_review(
        self,
        repo_full_name: str,
        pr_number: int,
        installation_id: int,
        body: str,
        event: str = "COMMENT",
        comments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a pull request review with optional inline comments."""

        token = await self.get_installation_token(installation_id)
        url = f"{self.settings.github_api_base_url}/repos/{repo_full_name}/pulls/{pr_number}/reviews"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        payload: dict[str, Any] = {"body": body, "event": event}
        if comments:
            payload["comments"] = comments

        response = await self._request("POST", url, headers=headers, json=payload)
        return dict(response.json())
