import json
import sys
from datetime import datetime
from pathlib import Path

log_path = Path.home() / "claude-lab" / "debug_event.log"

def main():
    event = json.load(sys.stdin)
    timestamp = datetime.now().isoformat()
    with open(log_path, "a") as f:
        f.write(f"{timestamp}\n")
        f.write(json.dumps(event, indent=2))
        f.write("\n---\n")

if __name__ == "__main__":
    main()