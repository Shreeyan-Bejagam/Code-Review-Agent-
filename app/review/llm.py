"""Anthropic Claude integration for structured review outputs."""

from __future__ import annotations

import json

import httpx
from pydantic import ValidationError

from app.config import get_settings
from app.models.schemas import Finding, InlineComment, ReviewResult, Severity


class LLMReviewer:
    """Calls Anthropic API and normalizes structured output."""

    def __init__(self) -> None:
        """Initialize configuration."""

        self.settings = get_settings()

    async def review_diff(self, prompt: str) -> ReviewResult:
        """Generate review findings from diff context."""

        if not self.settings.anthropic_api_key:
            return ReviewResult(
                summary="Anthropic API key not configured; completed Semgrep-only review.",
                findings=[],
                inline_comments=[],
                metadata={"provider": "disabled"},
            )

        headers = {
            "x-api-key": self.settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.settings.anthropic_model,
            "max_tokens": 1800,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.post(
                    f"{self.settings.anthropic_base_url}/v1/messages",
                    headers=headers,
                    json=payload,
                )
            response.raise_for_status()
            data = response.json()
            text_blocks = [item.get("text", "") for item in data.get("content", []) if item.get("type") == "text"]
            raw_json = "\n".join(text_blocks).strip()
            return self._parse_llm_json(raw_json)
        except (httpx.HTTPError, ValueError):
            return ReviewResult(
                summary="LLM review unavailable; completed Semgrep-only review.",
                findings=[],
                inline_comments=[],
                metadata={"provider": "anthropic_error"},
            )

    def _parse_llm_json(self, raw_json: str) -> ReviewResult:
        """Parse and validate model JSON output."""

        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError:
            return ReviewResult(summary="LLM output was not valid JSON.", findings=[], inline_comments=[])

        findings: list[Finding] = []
        for item in parsed.get("findings", []):
            try:
                findings.append(
                    Finding(
                        rule_id=str(item["rule_id"]),
                        title=str(item["title"]),
                        description=str(item["description"]),
                        severity=Severity(str(item["severity"])),
                        file_path=str(item["file_path"]),
                        line=int(item["line"]),
                        suggestion=item.get("suggestion"),
                        source="llm",
                    )
                )
            except (KeyError, TypeError, ValueError, ValidationError):
                continue

        comments: list[InlineComment] = []
        for item in parsed.get("inline_comments", []):
            try:
                comments.append(
                    InlineComment(
                        path=str(item["path"]),
                        line=int(item["line"]),
                        side="RIGHT",
                        body=str(item["body"]),
                    )
                )
            except (KeyError, TypeError, ValueError, ValidationError):
                continue

        return ReviewResult(
            summary=str(parsed.get("summary", "Automated review completed.")),
            findings=findings,
            inline_comments=comments,
            metadata={"provider": "anthropic"},
        )
