#!/usr/bin/env python3
"""notes_server.py — MCP server exposing notes tools to Claude Code."""

from pathlib import Path
from mcp.server.fastmcp import FastMCP

NOTES_DIR = Path.home() / "claude-lab" / "notes"

mcp = FastMCP("notes-server")


@mcp.tool()
def list_notes() -> str:
    """List all available notes in the notes directory."""
    files = sorted(NOTES_DIR.glob("*.md"))
    return "\n".join(f.name for f in files) if files else "No notes found."


@mcp.tool()
def read_note(filename: str) -> str:
    """Read a specific note by filename."""
    path = NOTES_DIR / filename
    if not path.exists():
        return f"Note '{filename}' not found."
    return path.read_text()


@mcp.tool()
def write_note(filename: str, content: str) -> str:
    """Write or overwrite a note with the given content."""
    path = NOTES_DIR / filename
    path.write_text(content)
    return f"Note '{filename}' written successfully."


if __name__ == "__main__":
    mcp.run()
