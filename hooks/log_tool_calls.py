#!/usr/bin/env python
import json
import sys
from datetime import datetime
from pathlib import Path

log_path = Path.home() / "claude-lab" / "tool_calls.log"


def main():
    event = json.load(sys.stdin)
    tool = event.get("tool_name", "unknown")
    tool_input = event.get("tool_input", {})
    session_id = event.get("session_id", "unknown")[:8]
    hook_event = event.get("hook_event_name", "unknown")
    timestamp = datetime.now().isoformat()

    with open(log_path, "a") as f:
        f.write(
            f"{timestamp} | {session_id} | {hook_event} | {tool} | {json.dumps(tool_input)}\n"
        )

        if hook_event == "PostToolUse":
            tool_response = event.get("tool_response", {})
            f.write(
                f"{timestamp} | {session_id} | RESPONSE | {tool} | {json.dumps(tool_response)}\n"
            )


if __name__ == "__main__":
    main()
