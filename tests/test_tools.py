#!/usr/bin/env python3
"""
M4.9 Tool Tests
Unit tests for list_notes and read_note from beta_tool_demo.
No API calls — tests tool functions directly.
"""

import pytest
from pathlib import Path
from unittest.mock import patch
from scripts.beta_tool_demo import list_notes, read_note

NOTES_DIR = Path.home() / "claude-lab" / "notes"

# ── list_notes tests ──────────────────────────────────────────────────────────


def test_list_notes_returns_known_file():
    """Happy path — a known note appears in results."""
    result = list_notes()
    assert "research_mcp.md" in result


def test_list_notes_returns_all_md_files():
    """All .md files in notes/ should appear in output."""
    result = list_notes()
    actual_files = sorted(NOTES_DIR.glob("*.md"))
    for f in actual_files:
        assert f.name in result


def test_list_notes_empty_directory():
    """When no notes exist, returns a clear message."""
    with patch("scripts.beta_tool_demo.NOTES_DIR") as mock_dir:
        mock_dir.glob.return_value = []
        result = list_notes()
    assert "No notes found" in result


# ── read_note tests ───────────────────────────────────────────────────────────


def test_read_note_returns_content():
    """Happy path — existing note returns its content."""
    result = read_note(filename="research_mcp.md")
    assert "Model Context Protocol" in result or "MCP" in result


def test_read_note_missing_file():
    """Missing file returns a clear not-found message."""
    result = read_note(filename="does_not_exist.md")
    assert "not found" in result.lower()


def test_read_note_returns_full_content():
    """Returned content matches what's actually on disk."""
    expected = (NOTES_DIR / "research_mcp.md").read_text()
    result = read_note(filename="research_mcp.md")
    assert result == expected
