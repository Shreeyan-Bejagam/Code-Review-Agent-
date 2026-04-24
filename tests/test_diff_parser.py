"""Tests for unified diff parser."""

from pathlib import Path

from app.github.diff_parser import parse_unified_diff


def test_parse_unified_diff_extracts_files_and_hunks() -> None:
    """Parse sample diff and assert hunk metadata and lines."""

    fixture_path = Path(__file__).parent / "fixtures" / "sample.diff"
    diff_text = fixture_path.read_text(encoding="utf-8")
    parsed = parse_unified_diff(diff_text)
    assert len(parsed) == 1
    file_diff = parsed[0]
    assert file_diff.new_path == "app/example.py"
    assert len(file_diff.hunks) == 1
    added_lines = [line for line in file_diff.hunks[0].lines if line.line_type == "add"]
    assert any("raise ValueError" in line.content for line in added_lines)
