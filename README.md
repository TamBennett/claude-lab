# claude-lab

A hands-on learning project for Claude Code CLI mastery — hooks, scripts, and SDK usage built as part of a structured training program toward Claude Certified Architect proficiency.

## Prerequisites

- [Claude Code CLI](https://docs.claude.com) installed and authenticated
- Python 3.9+
- `ANTHROPIC_API_KEY` set in your environment

## Setup

```bash
# Clone and enter
git clone https://github.com/TamBennett/claude-lab.git
cd claude-lab

# Create virtual environment and install SDK
python3 -m venv .venv
source .venv/bin/activate
pip install anthropic

# Set your API key (add to ~/.zprofile for persistence)
export ANTHROPIC_API_KEY="your-key-here"
```

## Project Structure

```
claude-lab/
├── hooks/
│   ├── log_tool_calls.py     # PreToolUse hook — logs all tool calls to tool_calls.log
│   └── debug_event.py        # Hook event payload inspector
├── notes/                    # Markdown notes consumed by summarize_notes.py
├── scripts/
│   ├── summarize_notes.py    # Reads notes/, produces summary.md via Claude Code --print
│   └── claude_cli.py         # Direct Anthropic SDK: simple call, streaming, multi-turn
├── .claude/
│   └── settings.json         # Project-level permissions and hook wiring
├── .mcp.json                 # Filesystem MCP server config
└── CLAUDE.md                 # Project-level Claude instructions
```

## Usage

```bash
# Summarize all markdown notes
python3 scripts/summarize_notes.py --notes-dir notes --output summary.md

# Call Claude directly via SDK
python3 scripts/claude_cli.py --mode simple    # single-turn completion
python3 scripts/claude_cli.py --mode stream    # streaming response
python3 scripts/claude_cli.py --mode multi     # multi-turn conversation
```

## Key Lessons

- `CLAUDE.md` scopes instructions at global (`~/.claude/CLAUDE.md`) and project level
- Hooks fire on `PreToolUse` — full audit trail for every tool call across sub-agents
- `CLAUDE_SESSION_ID` env var is unreliable in sub-agents; read `session_id` from the hook's stdin payload instead
- `--print` mode makes Claude Code scriptable but skips hooks — log at the script level instead
- MCP servers on macOS with Homebrew require the full binary path (`/opt/homebrew/bin/npx`)
- The Anthropic Python SDK is the foundation layer underneath Claude Code and Cowork
