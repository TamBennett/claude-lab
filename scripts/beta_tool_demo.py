#!/usr/bin/env python3
"""
M4.7 beta_tool Demo
Uses @beta_tool decorator instead of manual JSON schemas.
Compare the tool definitions here vs tool_use_demo.py — same result, less boilerplate.
"""

from pathlib import Path
from anthropic import Anthropic, beta_tool

NOTES_DIR = Path.home() / "claude-lab" / "notes"
client = Anthropic()

# ── Tool definitions — no manual JSON schema needed ───────────────────────────


@beta_tool
def list_notes() -> str:
    """List all available notes in the notes directory."""
    files = sorted(NOTES_DIR.glob("*.md"))
    return "\n".join(f.name for f in files) if files else "No notes found."


@beta_tool
def read_note(filename: str) -> str:
    """Read a specific note by filename."""
    path = NOTES_DIR / filename
    return path.read_text() if path.exists() else f"Note '{filename}' not found."


# Build tool list and dispatch map from decorated functions
tools = [list_notes.to_dict(), read_note.to_dict()]
tool_map = {"list_notes": list_notes, "read_note": read_note}

# ── Orchestration loop (same as M4.3) ────────────────────────────────────────


def run(user_message: str) -> str:
    print(f"\nUser: {user_message}\n")
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})
        print(f"stop_reason: {response.stop_reason}")

        if response.stop_reason == "end_turn":
            return next(b.text for b in response.content if hasattr(b, "text"))

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  → {block.name}({block.input})")
                    result = tool_map[block.name](**block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                        }
                    )
            messages.append({"role": "user", "content": tool_results})


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    answer = run("What notes do I have and what is the research_mcp note about?")
    print(f"\nClaude: {answer}")
