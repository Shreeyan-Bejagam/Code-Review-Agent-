"""Prompt templates for LLM-powered code review."""

from app.models.schemas import ParsedFileDiff


def build_review_prompt(parsed_files: list[ParsedFileDiff]) -> str:
    """Build a concise prompt from parsed diff hunks."""

    sections: list[str] = []
    for file_diff in parsed_files:
        hunks_preview = []
        for hunk in file_diff.hunks:
            added = [line for line in hunk.lines if line.line_type == "add"][:20]
            snippet = "\n".join(f"+{line.content}" for line in added)
            hunks_preview.append(f"{hunk.header}\n{snippet}")
        joined_hunks = "\n\n".join(hunks_preview)
        sections.append(f"File: {file_diff.new_path}\n{joined_hunks}")

    diff_context = "\n\n".join(sections)
    return (
        "You are a senior code reviewer focused on correctness, security, and reliability.\n"
        "Return strict JSON with keys: summary (string), findings (array), inline_comments (array).\n"
        "Each finding: rule_id, title, description, severity(low|medium|high|critical), file_path, line, suggestion.\n"
        "Each inline_comment: path, line, side(RIGHT), body.\n"
        "Only reference lines that exist in added code and avoid stylistic nitpicks.\n\n"
        f"DIFF CONTEXT:\n{diff_context}"
    )
