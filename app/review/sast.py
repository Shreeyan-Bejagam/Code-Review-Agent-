"""Semgrep execution and parsing helpers."""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
import tempfile
from pathlib import Path

from app.config import get_settings
from app.models.schemas import ParsedFileDiff, SemgrepResult, Severity


def _to_severity(raw: str) -> Severity:
    """Convert Semgrep severity text to app severity enum."""

    mapping = {
        "INFO": Severity.low,
        "WARNING": Severity.medium,
        "ERROR": Severity.high,
    }
    return mapping.get(raw.upper(), Severity.medium)


async def run_semgrep(parsed_files: list[ParsedFileDiff]) -> list[SemgrepResult]:
    """Run Semgrep on added snippets from the diff and return normalized results."""

    settings = get_settings()
    results: list[SemgrepResult] = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        for file_diff in parsed_files:
            target = root / file_diff.new_path
            target.parent.mkdir(parents=True, exist_ok=True)
            lines = []
            for hunk in file_diff.hunks:
                for line in hunk.lines:
                    if line.line_type == "add":
                        lines.append(line.content)
            if not lines:
                continue
            target.write_text("\n".join(lines) + "\n", encoding="utf-8")

        semgrep_bin = shutil.which("semgrep")
        if semgrep_bin:
            command = [semgrep_bin, "--json", "--config", settings.semgrep_config, str(root)]
        else:
            # Fallback for cases where worker runs from venv python but PATH does
            # not include venv bin scripts.
            command = [sys.executable, "-m", "semgrep", "--json", "--config", settings.semgrep_config, str(root)]

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        if not stdout:
            return results
        payload = json.loads(stdout.decode("utf-8"))
        for finding in payload.get("results", []):
            start = finding.get("start", {})
            extra = finding.get("extra", {})
            results.append(
                SemgrepResult(
                    check_id=str(finding.get("check_id", "semgrep.rule")),
                    path=str(finding.get("path", "")),
                    line=int(start.get("line", 1)),
                    message=str(extra.get("message", "Semgrep finding")),
                    severity=_to_severity(str(extra.get("severity", "WARNING"))),
                )
            )
    return results
