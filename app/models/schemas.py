"""Pydantic schemas used across the application."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class Severity(str, Enum):
    """Severity levels for findings."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ReviewStatus(str, Enum):
    """Status lifecycle for a review run."""

    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class PullRequestRef(BaseModel):
    """Minimal pull request metadata."""

    repository_full_name: str
    pull_request_number: int
    head_sha: str
    base_sha: str
    installation_id: int


class DiffLine(BaseModel):
    """A single line in a diff hunk."""

    line_type: str = Field(..., description="One of: context, add, del")
    content: str
    old_line: int | None = None
    new_line: int | None = None


class DiffHunk(BaseModel):
    """A parsed hunk from a unified diff."""

    file_path: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str
    lines: list[DiffLine]


class ParsedFileDiff(BaseModel):
    """A parsed file-level diff container."""

    old_path: str
    new_path: str
    hunks: list[DiffHunk]


class InlineComment(BaseModel):
    """Inline review comment for a specific file/line."""

    path: str
    line: int
    side: str = "RIGHT"
    body: str


class Finding(BaseModel):
    """Security or code quality issue found in PR changes."""

    rule_id: str
    title: str
    description: str
    severity: Severity
    file_path: str
    line: int
    suggestion: str | None = None
    source: str = Field(..., description="llm or semgrep")


class ReviewResult(BaseModel):
    """Combined review output from all analyzers."""

    summary: str
    findings: list[Finding]
    inline_comments: list[InlineComment]
    metadata: dict[str, Any] = Field(default_factory=dict)


class SemgrepResult(BaseModel):
    """Normalized Semgrep finding."""

    check_id: str
    path: str
    line: int
    message: str
    severity: Severity


class ReviewTaskPayload(BaseModel):
    """Queue payload used by the worker."""

    review_id: str
    pr: PullRequestRef
    diff_url: HttpUrl


class WebhookAck(BaseModel):
    """Response returned after webhook is accepted."""

    accepted: bool = True
    review_id: str
    queued_at: datetime
