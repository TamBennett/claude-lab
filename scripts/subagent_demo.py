#!/usr/bin/env python3
"""
M4.5 Sub-agent Demo
Spawns parallel sub-agents to summarize notes, then synthesizes with an orchestrator.
Demonstrates: asyncio.gather(), async Agent class, structured handoffs.
"""

import asyncio
import json
from pathlib import Path
import anthropic

NOTES_DIR = Path.home() / "claude-lab" / "notes"

# ── Tool definitions ──────────────────────────────────────────────────────────

read_note_tool = [
    {
        "name": "read_note",
        "description": "Read the contents of a specific note by filename.",
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
    }
]


def read_note(filename: str) -> str:
    path = NOTES_DIR / filename
    if not path.exists():
        return f"Note '{filename}' not found."
    return path.read_text()


# ── Async Agent class ─────────────────────────────────────────────────────────


class Agent:
    def __init__(
        self,
        name,
        system_prompt,
        tools,
        tool_functions,
        model="claude-haiku-4-5-20251001",
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools
        self.tool_functions = tool_functions
        self.model = model
        self.messages = []
        self.async_client = anthropic.AsyncAnthropic()

    async def run_async(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})

        while True:
            response = await self.async_client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tools if self.tools else anthropic.NOT_GIVEN,
                messages=self.messages,
            )

            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                return next(b.text for b in response.content if hasattr(b, "text"))

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
                    print(f"  [{self.name}] → {block.name}({json.dumps(block.input)})")
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                        }
                    )
        return results


# ── Sub-agent factory ─────────────────────────────────────────────────────────


async def summarize_note(filename: str) -> str:
    """Spawn one sub-agent to summarize a single note."""
    agent = Agent(
        name=f"summarizer:{filename}",
        system_prompt=(
            "You are a summarization agent. Read the note and return exactly "
            "one sentence summarizing its main point. No preamble, no formatting — "
            "just the sentence."
        ),
        tools=read_note_tool,
        tool_functions={"read_note": read_note},
    )
    return await agent.run_async(f"Summarize this note in one sentence: {filename}")


# ── Orchestrator ──────────────────────────────────────────────────────────────


async def orchestrate() -> str:
    # Step 1: discover notes
    notes = sorted(f.name for f in NOTES_DIR.glob("*.md"))
    print(f"Found {len(notes)} notes: {notes}\n")

    # Step 2: summarize all notes in parallel
    print("Spawning sub-agents in parallel...")
    import time

    start = time.time()

    summaries = await asyncio.gather(
        *[summarize_note(n) for n in notes], return_exceptions=True
    )

    elapsed = time.time() - start
    print(f"\nAll sub-agents finished in {elapsed:.1f}s\n")

    # Step 3: format summaries for handoff
    handoff = "\n".join(
        f"- {note}: {summary}"
        for note, summary in zip(notes, summaries)
        if not isinstance(summary, Exception)
    )
    print("Summaries collected:")
    print(handoff)

    # Step 4: orchestrator synthesizes
    print("\nOrchestrator synthesizing...\n")
    orchestrator = Agent(
        name="orchestrator",
        system_prompt=(
            "You are a synthesis agent. You receive one-sentence summaries of "
            "multiple notes. Write a single cohesive paragraph that captures "
            "the themes across all of them. No bullet points."
        ),
        tools=[],
        tool_functions={},
    )

    synthesis = await orchestrator.run_async(
        f"Here are summaries of all notes:\n{handoff}\n\n"
        "Write a single paragraph synthesizing the key themes."
    )

    return synthesis


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    result = asyncio.run(orchestrate())
    print(f"Final synthesis:\n{result}")
