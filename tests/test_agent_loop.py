#!/usr/bin/env python3
"""
M4.9 Agent Loop Tests
Mocked tests for the Agent class orchestration logic.
No API calls — Anthropic client is mocked.
"""

from unittest.mock import MagicMock, patch
from scripts.agent_demo import Agent, tools, tool_functions

# ── helpers ───────────────────────────────────────────────────────────────────


def make_end_turn_response(text):
    """Build a mock end_turn API response."""
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [MagicMock(text=text, spec=["text"])]
    return response


def make_tool_use_response(tool_name, tool_input, tool_id="tool_1"):
    """Build a mock tool_use API response."""
    response = MagicMock()
    response.stop_reason = "tool_use"
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input
    block.id = tool_id
    response.content = [block]
    return response


# ── tests ─────────────────────────────────────────────────────────────────────


def test_agent_returns_text_on_end_turn():
    """Agent extracts and returns text when stop_reason is end_turn."""
    with patch("anthropic.Anthropic") as MockClient:
        MockClient().messages.create.return_value = make_end_turn_response(
            "You have 4 notes."
        )
        agent = Agent("You are helpful.", tools, tool_functions)
        result = agent.run("What notes do I have?")

    assert result == "You have 4 notes."


def test_agent_appends_to_message_history():
    """Each run() call adds user + assistant messages to history."""
    with patch("anthropic.Anthropic") as MockClient:
        MockClient().messages.create.return_value = make_end_turn_response("Done.")
        agent = Agent("You are helpful.", tools, tool_functions)
        agent.run("Hello")

    assert len(agent.messages) == 2  # user + assistant


def test_agent_executes_tool_then_continues():
    """Agent calls tool on tool_use, sends result, returns on end_turn."""
    with patch("anthropic.Anthropic") as MockClient:
        MockClient().messages.create.side_effect = [
            make_tool_use_response("list_notes", {}),
            make_end_turn_response("You have 4 notes."),
        ]
        agent = Agent("You are helpful.", tools, tool_functions)
        result = agent.run("What notes do I have?")

    assert "4 notes" in result
    assert MockClient().messages.create.call_count == 2


def test_agent_handles_tool_error_gracefully():
    """Agent continues when tool raises an exception."""
    bad_tool_functions = {
        "list_notes": lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("disk error")
        ),
        "read_note": tool_functions["read_note"],
    }

    with patch("anthropic.Anthropic") as MockClient:
        MockClient().messages.create.side_effect = [
            make_tool_use_response("list_notes", {}),
            make_end_turn_response("Sorry, I encountered an error."),
        ]
        agent = Agent("You are helpful.", tools, bad_tool_functions)
        result = agent.run("What notes do I have?")

    assert result == "Sorry, I encountered an error."
