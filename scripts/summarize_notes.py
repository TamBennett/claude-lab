#!/usr/bin/env python3
"""
summarize_notes.py — reads all .md files in a notes/ directory
and uses Claude Code (subprocess) to produce a structured summary.
"""
import argparse
import subprocess
import sys
from pathlib import Path


def collect_notes(notes_dir: Path) -> str:
    """Read all markdown files and combine into a single prompt payload."""
    files = sorted(notes_dir.glob("*.md"))
    if not files:
        print(f"No .md files found in {notes_dir}")
        sys.exit(1)

    combined = ""
    for f in files:
        combined += f"## File: {f.name}\n\n"
        combined += f.read_text()
        combined += "\n\n---\n\n"

    print(f"Found {len(files)} note(s): {[f.name for f in files]}")
    return combined


def build_prompt(notes_content: str) -> str:
    return f"""You are a technical note summarizer. 

I will give you a set of notes. Produce a single structured summary document with these sections:
1. **Key Decisions** — any decisions made or recorded
2. **Action Items** — tasks assigned or self-assigned
3. **Key Concepts** — technical or conceptual points worth retaining
4. **Open Questions** — anything unresolved or flagged as a concern

Be concise. Use bullet points within each section. Do not invent content not present in the notes.

--- NOTES START ---
{notes_content}
--- NOTES END ---

Write the summary as a markdown document with a title and date stamp."""


def run_claude(prompt: str, output_path: Path) -> None:
    """Pass the prompt to Claude Code via subprocess and capture output."""
    from datetime import datetime
    log_path = Path.home() / "claude-lab" / "tool_calls.log"

    start = datetime.now().isoformat()
    result = subprocess.run(
        ["claude", "--print", prompt],
        capture_output=True,
        text=True
    )
    end = datetime.now().isoformat()

    with open(log_path, "a") as f:
        f.write(f"{start} | script | summarize_notes | started\n")
        f.write(f"{end} | script | summarize_notes | completed | returncode={result.returncode}\n")

    if result.returncode != 0:
        print(f"Claude error:\n{result.stderr}")
        sys.exit(1)

    output_path.write_text(result.stdout)
    print(f"Summary written to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Summarize notes using Claude Code")
    parser.add_argument("--notes-dir", default="notes", help="Directory containing .md notes")
    parser.add_argument("--output", default="summary.md", help="Output file path")
    args = parser.parse_args()

    notes_dir = Path(args.notes_dir)
    output_path = Path(args.output)

    if not notes_dir.exists():
        print(f"Notes directory '{notes_dir}' not found")
        sys.exit(1)

    notes_content = collect_notes(notes_dir)
    prompt = build_prompt(notes_content)
    run_claude(prompt, output_path)


if __name__ == "__main__":
    main()