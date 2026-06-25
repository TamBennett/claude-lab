#!/usr/bin/env python3
"""
M4.4 Agent Demo
Refactors the M4.3 tool use loop into a reusable Agent class.
Demonstrates persistent history across multi-turn conversations.
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


tool_functions = {"list_notes": lambda **kwargs: list_notes(), "read_note": read_note}

# ── Agent class ───────────────────────────────────────────────────────────────


class Agent:
    def __init__(
        self, system_prompt, tools, tool_functions, model="claude-haiku-4-5-20251001"
    ):
        self.system_prompt = system_prompt
        self.tools = tools
        self.tool_functions = tool_functions
        self.model = model
        self.messages = []
        self.client = anthropic.Anthropic()

    def run(self, user_message: str) -> str:
        print(f"\nUser: {user_message}")
        self.messages.append({"role": "user", "content": user_message})

        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tools,
                messages=self.messages,
            )

            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                answer = next(b.text for b in response.content if hasattr(b, "text"))
                print(f"Claude: {answer}")
                return answer

            if response.stop_reason == "tool_use":
                tool_results = self._execute_tools(response.content)
                self.messages.append({"role": "user", "content": tool_results})

    def _execute_tools(self, content_blocks):
        results = []
        for block in content_blocks:
            if block.type == "tool_use":
                fn = self.tool_functions.get(block.name)
                if fn:
                    try:
                        result = fn(**block.input)
                    except Exception as e:
                        result = f"Error: {e}"
                    print(
                        f"  → {block.name}({json.dumps(block.input)}) = {str(result)[:80]}"
                    )
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                        }
                    )
        return results


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    system_prompt = """You are a notes assistant with access to the user's notes directory.

When answering questions:
- Always check what notes exist before trying to read one by name
- Summarize note contents concisely — don't dump raw text at the user
- If a note doesn't exist, say so clearly
- You remember everything from earlier in the conversation

You have two tools: list_notes and read_note."""

    agent = Agent(system_prompt, tools, tool_functions)

    # Turn 1 — list notes
    agent.run("What notes do I have?")

    # Turn 2 — read a specific note
    agent.run("What is the research_mcp note about?")

    # Turn 3 — should use memory, no tool calls needed
    agent.run("Give me a one-sentence summary of everything you've read so far.")

    print(f"\n--- Message history: {len(agent.messages)} entries ---")
