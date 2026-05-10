#!/usr/bin/env python3
"""
M2.7 — Building CLI tools with Typer
claude_tools.py — a multi-command CLI wrapping your claude-lab scripts.

Commands:
  summarize   Summarize .md notes using Claude Code
  ask         Send a one-shot question to Claude via the Anthropic SDK
  schema      Print the JSON schema for a Pydantic model (dev utility)

Usage examples:
  python claude_tools.py --help
  python claude_tools.py summarize --help
  python claude_tools.py summarize --notes-dir notes --output summary.md
  python claude_tools.py ask "What is a Python decorator?"
  python claude_tools.py ask "Explain asyncio" --model claude-haiku-4-5-20251001 --max-tokens 256
  python claude_tools.py schema
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import typer
import anthropic
from typing_extensions import Annotated

# ─────────────────────────────────────────────────────────────────────────────
# App setup
#
# typer.Typer() creates the root CLI application.
# `invoke_without_command=True` lets `python claude_tools.py` (no subcommand)
# show help instead of erroring. `no_args_is_help=True` does the same thing
# when no arguments at all are passed.
# ─────────────────────────────────────────────────────────────────────────────

app = typer.Typer(
    name="claude-tools",
    help="CLI toolkit for your claude-lab scripts.",
    no_args_is_help=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND 1 — summarize
#
# Typer turns a plain Python function into a CLI command via @app.command().
# Function parameters become CLI options/arguments automatically:
#
#   - Parameters with defaults   → optional flags  (--notes-dir, --output)
#   - Parameters without defaults → required args  (would appear as positional)
#
# Annotated[type, typer.Option(...)] gives you full control:
#   - help=    the --help string for this flag
#   - show_default= whether to display the default in --help
#
# Typer converts Python snake_case → CLI kebab-case automatically:
#   notes_dir → --notes-dir
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def summarize(
    notes_dir: Annotated[
        Path,
        typer.Option(help="Directory containing .md note files.", show_default=True),
    ] = Path("notes"),
    output: Annotated[
        Path,
        typer.Option(help="Path for the generated summary markdown file.", show_default=True),
    ] = Path("summary.md"),
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Print the combined notes before summarizing."),
    ] = False,
) -> None:
    """Summarize all .md files in a directory using Claude Code."""

    # ── validate input ──
    if not notes_dir.exists():
        # typer.echo writes to stdout; typer.secho adds color
        typer.secho(f"Error: notes directory '{notes_dir}' not found.", fg=typer.colors.RED)
        raise typer.Exit(code=1)     # clean exit with non-zero code (like sys.exit(1))

    files = sorted(notes_dir.glob("*.md"))
    if not files:
        typer.secho(f"No .md files found in {notes_dir}.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    typer.echo(f"Found {len(files)} note(s): {[f.name for f in files]}")

    # ── build combined content ──
    combined = ""
    for f in files:
        combined += f"## File: {f.name}\n\n{f.read_text()}\n\n---\n\n"

    if verbose:
        typer.echo("\n── Combined notes ──")
        typer.echo(combined)

    # ── build prompt ──
    prompt = f"""You are a technical note summarizer.
Produce a structured summary with sections: Key Decisions, Action Items, Key Concepts, Open Questions.
Be concise. Use bullet points. Do not invent content not in the notes.

--- NOTES START ---
{combined}
--- NOTES END ---

Write the summary as a markdown document with a title and date stamp."""

    # ── call Claude Code via subprocess ──
    typer.echo("Calling Claude Code...")
    log_path = Path.home() / "claude-lab" / "tool_calls.log"
    start = datetime.now().isoformat()

    result = subprocess.run(
        ["claude", "--print", prompt], capture_output=True, text=True
    )

    with open(log_path, "a") as f:
        f.write(f"{start} | script | claude_tools.summarize | returncode={result.returncode}\n")

    if result.returncode != 0:
        typer.secho(f"Claude error:\n{result.stderr}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    output.write_text(result.stdout)
    typer.secho(f"Summary written to {output}", fg=typer.colors.GREEN)


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND 2 — ask
#
# This command takes a REQUIRED positional argument (question) — no default,
# no Option wrapper. Typer makes it a required CLI argument:
#   python claude_tools.py ask "your question here"
#
# The remaining parameters are options with defaults — all optional flags.
#
# typer.Argument vs typer.Option:
#   Argument  → positional: `ask "question"`
#   Option    → named flag: `ask --question "question"`
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def ask(
    question: Annotated[
        str,
        typer.Argument(help="The question to send to Claude."),
    ],
    model: Annotated[
        str,
        typer.Option(help="Claude model to use."),
    ] = "claude-haiku-4-5-20251001",
    max_tokens: Annotated[
        int,
        typer.Option(help="Maximum tokens in the response.", min=1, max=4096),
    ] = 512,
    stream: Annotated[
        bool,
        typer.Option("--stream", "-s", help="Stream the response token by token."),
    ] = False,
) -> None:
    """Send a one-shot question to Claude via the Anthropic SDK."""

    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        typer.secho("Error: ANTHROPIC_API_KEY not set.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    client = anthropic.Anthropic(api_key=api_key)

    typer.secho(f"Model: {model}  |  max_tokens: {max_tokens}", fg=typer.colors.BRIGHT_BLACK)
    typer.echo("")

    if stream:
        # Streaming: print tokens as they arrive
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": question}],
        ) as stream_ctx:
            for text in stream_ctx.text_stream:
                typer.echo(text, nl=False)
        typer.echo("")   # newline after stream ends
    else:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": question}],
        )
        typer.echo(response.content[0].text)


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND 3 — schema
#
# A dev-utility command: print the JSON schema Pydantic generates for a model.
# Demonstrates: importing from another script, Typer choices via Enum.
#
# The `model_name` argument is constrained to a fixed set of strings.
# Typer validates the input and shows valid choices in --help automatically.
# ─────────────────────────────────────────────────────────────────────────────

from enum import Enum

class ModelName(str, Enum):
    user_profile = "UserProfile"
    search_files = "SearchFilesInput"


@app.command()
def schema(
    model_name: Annotated[
        ModelName,
        typer.Argument(help="Which Pydantic model to print the schema for."),
    ] = ModelName.user_profile,
    indent: Annotated[
        int,
        typer.Option(help="JSON indentation level.", min=0, max=8),
    ] = 2,
) -> None:
    """Print the JSON schema for a Pydantic model (as Claude would receive it)."""

    # Import the models from your existing pydantic_demo script
    scripts_dir = Path(__file__).parent / "scripts"
    sys.path.insert(0, str(scripts_dir))
    from pydantic_demo import UserProfile, SearchFilesInput

    models = {
        ModelName.user_profile: UserProfile,
        ModelName.search_files: SearchFilesInput,
    }

    target = models[model_name]
    typer.secho(f"\nSchema for {target.__name__}:\n", fg=typer.colors.CYAN)
    typer.echo(json.dumps(target.model_json_schema(), indent=indent))


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
#
# `if __name__ == "__main__": app()` is the Typer equivalent of main().
# When run as a script, Typer parses sys.argv and dispatches to the right command.
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
