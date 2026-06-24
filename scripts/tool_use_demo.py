#!/usr/bin/env python3
"""
M4.3 Tool Use Demo
Demonstrates multi-tool orchestration with the Anthropic SDK.
Tools: list_notes, read_note
"""

import json
from pathlib import Path
import anthropic

NOTES_DIR = Path.home() / "claude-lab" / "notes"
client = anthropic.Anthropic()

# ── Tool definitions ──────────────────────────────────────────────────────────

tools = [
    {
        "name": "list_notes",
        "description": "List all available notes (markdown files) in the notes directory. Use this when the user wants to know what notes exist.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "read_note",
        "description": "Read the contents of a specific note by filename. Use this when the user wants to know what a note contains.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The filename of the note to read, e.g. 'meeting-notes.md'",
                }
            },
            "required": ["filename"],
        },
    },
]

# ── Tool implementations ──────────────────────────────────────────────────────


def list_notes() -> str:
    files = list(NOTES_DIR.glob("*.md"))
    if not files:
        return "No notes found."
    return "\n".join(f.name for f in sorted(files))


def read_note(filename: str) -> str:
    path = NOTES_DIR / filename
    if not path.exists():
        return f"Note '{filename}' not found."
    return path.read_text()


# Map tool names to functions
tool_functions = {"list_notes": lambda **kwargs: list_notes(), "read_note": read_note}

# ── Orchestration loop ────────────────────────────────────────────────────────


def run_with_tools(user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]
    print(f"\nUser: {user_message}\n")

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

        print(f"stop_reason: {response.stop_reason}")
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            return response.content[0].text

        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    print(
                        f"  → Claude calling: {block.name}({json.dumps(block.input)})"
                    )
                    fn = tool_functions[block.name]
                    result = fn(**block.input)
                    print(
                        f"  ← Result: {result[:80]}{'...' if len(result) > 80 else ''}"
                    )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            messages.append({"role": "user", "content": tool_results})


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    answer = run_with_tools("What notes do I have and what is the first one about?")
    print(f"\nClaude: {answer}")
