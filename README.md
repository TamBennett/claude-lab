# claude-lab

# claude-lab

Learning project for Claude Code CLI mastery. Built as part of a structured training development program.

## What's here

### Hooks

`hooks/log_tool_calls.py` — PreToolUse hook that logs every Claude tool call to `tool_calls.log`.  
Captures: timestamp, session ID, hook event, tool name, tool input.

### Scripts

`scripts/summarize_notes.py` — reads all `.md` files in `notes/` and produces a structured `summary.md` using Claude Code (`--print` mode).  
`scripts/claude_cli.py` — CLI tool demonstrating direct Anthropic SDK usage: simple call, streaming, and multi-turn conversation.

### Config

`.claude/settings.json` — project-level permissions (allow/deny rules) and hook wiring.  
`.mcp.json` — filesystem MCP server config (note: user-scoped in `~/.claude.json` due to macOS PATH constraints).  
`CLAUDE.md` — project-level Claude instructions.

## Setup

```bash
# Clone and enter
git clone https://github.com/TamBennett/claude-lab.git
cd claude-lab

# Python dependencies (for SDK scripts)
python3 -m venv .venv
source .venv/bin/activate
pip install anthropic

# Set your API key
export ANTHROPIC_API_KEY="your-key-here"
```

## Usage

```bash
# Summarize notes
python3 scripts/summarize_notes.py --notes-dir notes --output summary.md

# Call Claude directly via SDK
python3 scripts/claude_cli.py --mode simple
python3 scripts/claude_cli.py --mode stream
python3 scripts/claude_cli.py --mode multi
```

## Key lessons

- CLAUDE.md scopes instructions at global and project level
- Hooks fire on PreToolUse — full audit trail for every tool call
- MCP servers extend Claude's toolset; stdio transport is standard for local servers
- `--print` mode makes Claude Code scriptable but skips hooks — log at the script level instead
- The Anthropic SDK is the layer underneath Claude Code and Cowork
