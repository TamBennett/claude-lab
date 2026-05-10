"""
M2.5 — Environment Variables: python-dotenv, .env files, secrets management
Exercises for claude-lab/scripts/env_demo.py

Four sections:
  1. os.environ basics — read, default, missing key behavior
  2. load_dotenv() — loading .env into os.environ
  3. get_required_env() — fail-fast helper pattern
  4. Real AsyncAnthropic call using dotenv-loaded key
"""

import asyncio
import os

import anthropic
from dotenv import load_dotenv


# ─────────────────────────────────────────────
# SECTION 1 — os.environ basics
# Demonstrates: dict-like access, get() with default, KeyError on missing key.
# ─────────────────────────────────────────────

def section_1() -> None:
    print("=== Section 1: os.environ basics ===\n")

    # os.environ is a dict-like object — standard dict methods apply
    print(f"  HOME:      {os.environ.get('HOME', 'not set')}")
    print(f"  SHELL:     {os.environ.get('SHELL', 'not set')}")
    print(f"  FAKE_VAR:  {os.environ.get('FAKE_VAR', 'not set')}")

    # .get() never raises — returns None or your default
    val = os.environ.get("FAKE_VAR")
    print(f"\n  os.environ.get('FAKE_VAR') with no default: {val!r}  (None, not an error)")

    # Direct access raises KeyError if missing
    print("\n  --- KeyError on missing key ---")
    try:
        _ = os.environ["FAKE_VAR"]
    except KeyError as e:
        print(f"  KeyError: {e}")

    # Check membership
    has_key = "ANTHROPIC_API_KEY" in os.environ
    print(f"\n  'ANTHROPIC_API_KEY' in os.environ (before load_dotenv): {has_key}")


# ─────────────────────────────────────────────
# SECTION 2 — load_dotenv()
# Demonstrates: .env loading, no-override behavior, override=True.
# ─────────────────────────────────────────────

def section_2() -> None:
    print("\n=== Section 2: load_dotenv() ===\n")

    # load_dotenv() reads .env from cwd (or walks up to find it)
    # Does NOT override vars already set in the shell environment
    loaded = load_dotenv()
    print(f"  load_dotenv() found and loaded a .env file: {loaded}")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "not set")
    # Only show first/last 6 chars — never print a full API key
    if api_key != "not set":
        masked = f"{api_key[:10]}...{api_key[-4:]}"
    else:
        masked = "not set"
    print(f"  ANTHROPIC_API_KEY after load_dotenv: {masked}")

    # load_dotenv(override=True) forces .env values to win over shell vars
    # Useful when testing with a different key without changing your shell
    load_dotenv(override=True)
    print(f"  load_dotenv(override=True) — .env values now take precedence over shell")

    # Demonstrate that load_dotenv is idempotent — safe to call multiple times
    load_dotenv()
    load_dotenv()
    print(f"  Calling load_dotenv() multiple times is safe — no side effects")


# ─────────────────────────────────────────────
# SECTION 3 — get_required_env() helper
# Demonstrates: fail-fast pattern for required secrets.
# ─────────────────────────────────────────────

def get_required_env(key: str) -> str:
    """Read a required environment variable. Raise clearly if missing or empty."""
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(
            f"Required environment variable '{key}' is not set.\n"
            f"Add it to your .env file or export it in your shell."
        )
    return value


def section_3() -> None:
    print("\n=== Section 3: get_required_env() fail-fast helper ===\n")

    # Should succeed — ANTHROPIC_API_KEY is set (loaded in section 2)
    try:
        key = get_required_env("ANTHROPIC_API_KEY")
        masked = f"{key[:10]}...{key[-4:]}"
        print(f"  get_required_env('ANTHROPIC_API_KEY'): {masked}  ✓")
    except RuntimeError as e:
        print(f"  RuntimeError: {e}")

    # Should fail — FAKE_SECRET is not set anywhere
    print("\n  --- RuntimeError on missing required var ---")
    try:
        get_required_env("FAKE_SECRET")
    except RuntimeError as e:
        print(f"  RuntimeError: {e}")


# ─────────────────────────────────────────────
# SECTION 4 — Real AsyncAnthropic call using dotenv-loaded key
# Demonstrates: the full production pattern — load_dotenv at top of script,
#               get_required_env to validate, pass explicitly to client.
# ─────────────────────────────────────────────

async def section_4() -> None:
    print("\n=== Section 4: AsyncAnthropic call with dotenv-loaded key ===\n")

    # Best practice: pass the key explicitly rather than relying on the SDK
    # to find it in the environment — makes the dependency visible.
    api_key = get_required_env("ANTHROPIC_API_KEY")
    client = anthropic.AsyncAnthropic(api_key=api_key)

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=128,
        messages=[{
            "role": "user",
            "content": "In one sentence: why should API keys never be committed to git?",
        }],
    )

    print(f"  Claude says: {response.content[0].text}")


# ─────────────────────────────────────────────
# MAIN
# load_dotenv() at module top — standard practice.
# All subsequent os.environ reads see the .env values.
# ─────────────────────────────────────────────

async def main() -> None:
    section_1()
    section_2()
    section_3()
    await section_4()


if __name__ == "__main__":
    load_dotenv()   # load once at entry point before anything else runs
    asyncio.run(main())
