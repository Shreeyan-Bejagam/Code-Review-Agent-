

from __future__ import annotations

import re

from app.models.schemas import DiffHunk, DiffLine, ParsedFileDiff

HUNK_RE = re.compile(r"^@@ -(?P<old_start>\d+)(,(?P<old_count>\d+))? \+(?P<new_start>\d+)(,(?P<new_count>\d+))? @@")


def parse_unified_diff(diff_text: str) -> list[ParsedFileDiff]:


    files: list[ParsedFileDiff] = []
    current_file: ParsedFileDiff | None = None
    current_hunk: DiffHunk | None = None
    old_line = 0
    new_line = 0

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            if current_file is not None:
                if current_hunk is not None:
                    current_file.hunks.append(current_hunk)
                    current_hunk = None
                files.append(current_file)
            current_file = ParsedFileDiff(old_path="", new_path="", hunks=[])
            continue

        if current_file is None:
            continue

        if line.startswith("--- "):
            current_file.old_path = line.removeprefix("--- ").removeprefix("a/")
            continue
        if line.startswith("+++ "):
            current_file.new_path = line.removeprefix("+++ ").removeprefix("b/")
            continue

        hunk_match = HUNK_RE.match(line)
        if hunk_match:
            if current_hunk is not None:
                current_file.hunks.append(current_hunk)
            old_start = int(hunk_match.group("old_start"))
            new_start = int(hunk_match.group("new_start"))
            old_count = int(hunk_match.group("old_count") or "1")
            new_count = int(hunk_match.group("new_count") or "1")
            current_hunk = DiffHunk(
                file_path=current_file.new_path or current_file.old_path,
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
                header=line,
                lines=[],
            )
            old_line = old_start
            new_line = new_start
            continue

        if current_hunk is None:
            continue
        if line.startswith("\\ No newline at end of file"):
            continue
        if line.startswith("+"):
            current_hunk.lines.append(DiffLine(line_type="add", content=line[1:], new_line=new_line))
            new_line += 1
        elif line.startswith("-"):
            current_hunk.lines.append(DiffLine(line_type="del", content=line[1:], old_line=old_line))
            old_line += 1
        else:
            context = line[1:] if line.startswith(" ") else line
            current_hunk.lines.append(
                DiffLine(line_type="context", content=context, old_line=old_line, new_line=new_line)
            )
            old_line += 1
            new_line += 1

    if current_file is not None:
        if current_hunk is not None:
            current_file.hunks.append(current_hunk)
        files.append(current_file)
    return files
