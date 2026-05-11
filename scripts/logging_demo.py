#!/usr/bin/env python3
"""
M2.8 — Logging and error handling patterns for agent code
logging_demo.py — structured logging, custom exceptions, retry patterns.

Sections:
  1. Python logging basics — loggers, handlers, levels, formatters
  2. Structured JSON logging — machine-parseable log lines
  3. Custom exception hierarchy — typed errors for agent failures
  4. Retry with tenacity — handling rate limits and transient errors
  5. Full agent pattern — all pieces wired together

Run:
  python logging_demo.py
"""

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — Python logging basics
#
# The logging module has four key objects:
#
#   Logger    — what your code calls: logger.info(), logger.error(), etc.
#               Get one with logging.getLogger(__name__).
#               __name__ = the module name — keeps loggers namespaced.
#
#   Handler   — where log records go: StreamHandler (stdout/stderr),
#               FileHandler (a file), RotatingFileHandler (capped file), etc.
#               One logger can have multiple handlers.
#
#   Formatter — how a log record looks: plain text, JSON, etc.
#               Attached to a Handler, not a Logger.
#
#   Level     — DEBUG < INFO < WARNING < ERROR < CRITICAL
#               Logger and Handler each have a level; both must pass
#               for a record to appear.
#
# Why not just use print()?
#   - print() has no level filtering — can't silence debug noise in production
#   - print() has no timestamps, caller info, or structured data
#   - print() can't route to multiple destinations (file + stdout) simultaneously
#   - logging is the standard — other libraries (anthropic SDK, httpx) emit
#     logs you can capture and filter alongside your own
# ─────────────────────────────────────────────────────────────────────────────

def section_1() -> None:
    print("\n" + "="*60)
    print("SECTION 1 — Python logging basics")
    print("="*60)

    # Get a logger named after this module.
    # Convention: always use __name__ — gives you the module path as the name.
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)     # accept everything DEBUG and above

    # Handler: write to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    # Formatter: plain text with timestamp, level, logger name, message
    # %(asctime)s  — human-readable timestamp
    # %(name)s     — logger name (= __name__ = "__main__" here)
    # %(levelname) — DEBUG / INFO / WARNING / ERROR / CRITICAL
    # %(message)s  — the string you passed to logger.info() etc.
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Emit one record at each level
    logger.debug("debug: verbose detail — disabled in production")
    logger.info("info: normal operation — a tool call started")
    logger.warning("warning: something unexpected but recoverable")
    logger.error("error: something failed — action required")
    logger.critical("critical: system is broken — page someone")

    # Level filtering: raise the handler level to WARNING
    # DEBUG and INFO records are now silenced
    handler.setLevel(logging.WARNING)
    print("\n  [handler level raised to WARNING — DEBUG and INFO suppressed]")
    logger.debug("this will NOT appear")
    logger.info("this will NOT appear")
    logger.warning("this WILL appear")

    # exc_info=True: attach the current exception's traceback to the log record
    print("\n  [logging an exception with traceback]")
    try:
        1 / 0
    except ZeroDivisionError:
        logger.error("caught an exception", exc_info=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Structured JSON logging
#
# Plain text logs are readable but hard to query. When a Claude agent makes
# 50 tool calls in one session, you want to ask:
#   "Show me all tool calls where tool_name=read_file AND duration_ms > 200"
#
# JSON logs make this trivial — each line is a parseable dict.
# Tools like jq, Datadog, Splunk, and CloudWatch all consume JSON logs natively.
#
# Pattern: write a custom Formatter that serializes a dict instead of a string.
# ─────────────────────────────────────────────────────────────────────────────

class JsonFormatter(logging.Formatter):
    """
    Formats each log record as a single-line JSON object.

    Every line contains:
      timestamp   — ISO 8601 UTC
      level       — DEBUG / INFO / WARNING / ERROR / CRITICAL
      logger      — module name
      message     — the log message string
      ...extras   — any kwargs passed via `extra={}` in the log call
      exception   — traceback string if exc_info=True
    """

    def format(self, record: logging.LogRecord) -> str:
        # Base fields always present
        payload: dict = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Extra fields: anything in record.__dict__ that isn't a standard field.
        # When you call logger.info("msg", extra={"tool": "read_file"}),
        # "tool" lands directly on the LogRecord — we fish it back out here.
        standard_keys = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in standard_keys:
                payload[key] = value

        # Attach exception traceback if present
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload)


def make_json_logger(name: str, log_path: Path) -> logging.Logger:
    """
    Return a logger that writes JSON to both a file and stdout.
    Call this once per module; pass the logger around or store it as a global.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # File handler — append mode, JSON lines
    fh = logging.FileHandler(log_path, mode="a")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(JsonFormatter())

    # Console handler — plain text for human readability during development
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s",
                                       datefmt="%H:%M:%S"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def section_2() -> None:
    print("\n" + "="*60)
    print("SECTION 2 — Structured JSON logging")
    print("="*60)

    log_path = Path.home() / "claude-lab" / "agent.log"
    logger = make_json_logger("agent.demo", log_path)

    # Basic structured log — extra fields become JSON keys
    logger.info(
        "tool call started",
        extra={
            "session_id": "sess_abc123",
            "tool_name": "read_file",
            "input": {"path": "/notes/meeting.md"},
        },
    )

    # Simulated tool call result
    logger.info(
        "tool call completed",
        extra={
            "session_id": "sess_abc123",
            "tool_name": "read_file",
            "duration_ms": 42,
            "bytes_read": 1024,
        },
    )

    # Error with context
    try:
        raise FileNotFoundError("/notes/missing.md")
    except FileNotFoundError as e:
        logger.error(
            "tool call failed",
            exc_info=True,
            extra={
                "session_id": "sess_abc123",
                "tool_name": "read_file",
                "input": {"path": "/notes/missing.md"},
            },
        )

    print(f"\n  JSON log written to: {log_path}")
    print("  Last 2 lines of agent.log:")
    lines = log_path.read_text().strip().split("\n")
    for line in lines[-2:]:
        print(" ", json.dumps(json.loads(line), indent=2))


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — Custom exception hierarchy
#
# In agent code, errors have different meanings:
#   - A missing file is a user error (bad input)
#   - A rate limit is a transient API error (retry)
#   - An auth failure is a config error (don't retry — fix the key)
#   - A tool schema mismatch is a developer error (fix the code)
#
# Raising plain Exception tells callers nothing about what happened or
# whether to retry. A typed hierarchy lets callers make that decision:
#
#   except TransientAgentError:   → retry
#   except ConfigurationError:    → abort with clear message
#   except ToolError:             → log and report to Claude
# ─────────────────────────────────────────────────────────────────────────────

class AgentError(Exception):
    """
    Base class for all agent errors.
    Catch this when you want to handle any agent failure generically.
    Always include a message and optional context dict.
    """
    def __init__(self, message: str, context: dict | None = None):
        super().__init__(message)
        self.context = context or {}

    def __str__(self) -> str:
        if self.context:
            return f"{super().__str__()} | context={self.context}"
        return super().__str__()


class TransientAgentError(AgentError):
    """Temporary failure — safe to retry. E.g. rate limit, network timeout."""
    pass


class ConfigurationError(AgentError):
    """Bad configuration — retrying won't help. E.g. missing API key, bad model name."""
    pass


class ToolError(AgentError):
    """A tool call failed. Includes tool name and input for debugging."""
    def __init__(self, message: str, tool_name: str, tool_input: dict):
        super().__init__(message, context={"tool_name": tool_name, "tool_input": tool_input})
        self.tool_name = tool_name
        self.tool_input = tool_input


class RateLimitError(TransientAgentError):
    """Anthropic API rate limit hit. Always retry with backoff."""
    pass


def section_3() -> None:
    print("\n" + "="*60)
    print("SECTION 3 — Custom exception hierarchy")
    print("="*60)

    # ToolError — structured context preserved on the exception object
    try:
        raise ToolError(
            "read_file: path does not exist",
            tool_name="read_file",
            tool_input={"path": "/missing/file.md"},
        )
    except ToolError as e:
        print(f"\n  Caught ToolError:  {e}")
        print(f"  tool_name:         {e.tool_name}")
        print(f"  tool_input:        {e.tool_input}")
        print(f"  context dict:      {e.context}")

    # ConfigurationError — caller knows not to retry
    try:
        raise ConfigurationError(
            "ANTHROPIC_API_KEY is not set",
            context={"env_var": "ANTHROPIC_API_KEY"},
        )
    except ConfigurationError as e:
        print(f"\n  Caught ConfigurationError: {e}")
        print(f"  Retrying would not help — aborting.")

    # Catching by base class — generic handler for any agent error
    errors = [
        TransientAgentError("network timeout"),
        ConfigurationError("bad model name"),
        ToolError("write failed", tool_name="write_file", tool_input={"path": "/ro/file"}),
    ]
    print("\n  Catching all AgentErrors by base class:")
    for err in errors:
        try:
            raise err
        except AgentError as e:
            print(f"    {type(e).__name__}: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — Retry with tenacity
#
# The Anthropic API returns HTTP 429 (rate limit) and occasional 529 (overload).
# These are transient — waiting and retrying is the right response.
# Retrying immediately on a rate limit makes it worse.
#
# tenacity decorators compose to define retry policy:
#
#   @retry(
#       retry=retry_if_exception_type(RateLimitError),  # only retry this type
#       stop=stop_after_attempt(4),                     # give up after 4 tries
#       wait=wait_exponential(multiplier=1, min=2, max=30), # 2s, 4s, 8s, 16s...
#       before_sleep=before_sleep_log(logger, logging.WARNING), # log each wait
#   )
#
# wait_exponential: each retry waits 2× longer than the previous.
# This is "exponential backoff" — standard practice for API rate limits.
# ─────────────────────────────────────────────────────────────────────────────

_retry_logger = logging.getLogger("agent.retry")
_retry_logger.addHandler(logging.StreamHandler(sys.stdout))
_retry_logger.setLevel(logging.DEBUG)


def _make_api_call(client: anthropic.Anthropic, question: str) -> str:
    """
    Inner function: makes one API call attempt.
    Converts Anthropic SDK exceptions to our typed hierarchy.
    Callers should not call this directly — use call_claude() below.
    """
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=128,
            messages=[{"role": "user", "content": question}],
        )
        return response.content[0].text
    except anthropic.RateLimitError as e:
        # Convert SDK exception → our typed exception → tenacity retries it
        raise RateLimitError(f"Rate limit hit: {e}", context={"status": 429}) from e
    except anthropic.APIConnectionError as e:
        raise TransientAgentError(f"Connection error: {e}") from e
    except anthropic.AuthenticationError as e:
        # Auth failures are config errors — do NOT retry
        raise ConfigurationError(f"Auth failed: {e}") from e


@retry(
    retry=retry_if_exception_type(TransientAgentError),  # RateLimitError is a subclass
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(_retry_logger, logging.WARNING),
    reraise=True,   # if all retries exhausted, re-raise the last exception
)
def call_claude(client: anthropic.Anthropic, question: str) -> str:
    """
    Public API: calls Claude with automatic retry on transient errors.
    ConfigurationError propagates immediately (no retry).
    TransientAgentError and RateLimitError are retried up to 4 times.
    """
    return _make_api_call(client, question)


def section_4() -> None:
    print("\n" + "="*60)
    print("SECTION 4 — Retry with tenacity")
    print("="*60)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("  ANTHROPIC_API_KEY not set — skipping live call demo")
        return

    client = anthropic.Anthropic(api_key=api_key)

    # ── Happy path: no retry needed ──
    print("\n  [happy path — should succeed on first attempt]")
    try:
        answer = call_claude(client, "In one sentence: what is exponential backoff?")
        print(f"  Claude: {answer}")
    except AgentError as e:
        print(f"  Failed: {e}")

    # ── Simulate retry behavior without hitting the real API ──
    # We manually raise TransientAgentError N times then succeed.
    print("\n  [simulated retry — fails twice, succeeds on attempt 3]")
    attempt_count = 0

    @retry(
        retry=retry_if_exception_type(TransientAgentError),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=0.1, min=0.1, max=1),  # fast for demo
        before_sleep=before_sleep_log(_retry_logger, logging.WARNING),
        reraise=True,
    )
    def flaky_operation() -> str:
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise TransientAgentError(
                f"simulated transient failure on attempt {attempt_count}"
            )
        return f"success on attempt {attempt_count}"

    try:
        result = flaky_operation()
        print(f"  Result: {result}")
    except TransientAgentError as e:
        print(f"  All retries exhausted: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — Full agent pattern
#
# Wiring everything together into the pattern you'll use in M4 agents:
#   - Session ID for correlation across log lines
#   - JSON logger for structured output
#   - Custom exceptions for typed error handling
#   - Retry decorator on the API call
#   - Context captured at every log point (what went in, what came out)
# ─────────────────────────────────────────────────────────────────────────────

def run_agent_session(question: str) -> None:
    """
    A minimal but production-quality agent invocation pattern.
    Every log line shares the same session_id — trivial to grep/query.
    """
    session_id = str(uuid.uuid4())[:8]   # short ID for readability
    log_path = Path.home() / "claude-lab" / "agent.log"
    logger = make_json_logger(f"agent.session.{session_id}", log_path)

    logger.info(
        "session started",
        extra={"session_id": session_id, "question": question},
    )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        err = ConfigurationError("ANTHROPIC_API_KEY not set")
        logger.error(
            "configuration error",
            exc_info=False,
            extra={"session_id": session_id, "error": str(err)},
        )
        raise err

    client = anthropic.Anthropic(api_key=api_key)
    start = time.monotonic()

    try:
        answer = call_claude(client, question)
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "session completed",
            extra={
                "session_id": session_id,
                "duration_ms": duration_ms,
                "answer_chars": len(answer),
            },
        )
        print(f"\n  [{session_id}] Claude: {answer}")

    except TransientAgentError as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.error(
            "session failed after retries",
            exc_info=True,
            extra={
                "session_id": session_id,
                "duration_ms": duration_ms,
                "error_type": type(e).__name__,
                "context": e.context,
            },
        )
        raise

    except ConfigurationError as e:
        logger.error(
            "session aborted — configuration error",
            extra={"session_id": session_id, "error": str(e)},
        )
        raise


def section_5() -> None:
    print("\n" + "="*60)
    print("SECTION 5 — Full agent pattern")
    print("="*60)

    print("\n  Running agent session with structured logging...")
    try:
        run_agent_session("In one sentence: why does structured logging beat plain text?")
    except AgentError as e:
        print(f"  Agent error: {e}")

    # Show what the JSON log looks like
    log_path = Path.home() / "claude-lab" / "agent.log"
    if log_path.exists():
        lines = log_path.read_text().strip().split("\n")
        session_lines = [l for l in lines if "session" in l]
        if session_lines:
            print(f"\n  Last session log entry (JSON):")
            print("  " + json.dumps(json.loads(session_lines[-1]), indent=2))


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    section_1()
    section_2()
    section_3()
    section_4()
    section_5()
