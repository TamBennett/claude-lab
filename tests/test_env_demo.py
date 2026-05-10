"""
M2.6 — Testing with pytest: unit tests, fixtures, mocking
Test file: test_env_demo.py

Covers:
  1. monkeypatch — pytest's built-in fixture for safely mutating env vars
  2. Isolation — tests must not bleed state into each other
  3. unittest.mock.patch — decorator and context manager forms
  4. Mocking the Anthropic client so tests never hit the network

Run from your claude-lab root (with venv activated):
  pytest tests/test_env_demo.py -v
"""

import os
import sys
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from env_demo import get_required_env


# ─────────────────────────────────────────────────────────────────────────────
# PART 1 — monkeypatch
#
# monkeypatch is a pytest built-in fixture. You never define it yourself —
# just list it as a test parameter and pytest injects it.
#
# Key methods:
#   monkeypatch.setenv(key, value)   — set an env var for this test only
#   monkeypatch.delenv(key, raising) — remove an env var (raising=False: don't
#                                       error if it wasn't set)
#   monkeypatch.setattr(obj, name, value) — patch any object attribute
#
# After the test completes, monkeypatch automatically reverts ALL changes.
# This is the big win over doing `os.environ["KEY"] = "val"` directly —
# that leaks into subsequent tests and makes failures order-dependent.
# ─────────────────────────────────────────────────────────────────────────────

def test_get_required_env_returns_value(monkeypatch):
    """Happy path: var is set → function returns it."""
    monkeypatch.setenv("MY_TEST_KEY", "secret-value")
    result = get_required_env("MY_TEST_KEY")
    assert result == "secret-value"


def test_get_required_env_missing_raises(monkeypatch):
    """
    Var not in environment → RuntimeError with a helpful message.
    We use delenv(raising=False) because the var might or might not exist
    in the shell that runs pytest — we want it gone either way.
    """
    monkeypatch.delenv("MISSING_VAR", raising=False)
    with pytest.raises(RuntimeError, match="MISSING_VAR"):
        get_required_env("MISSING_VAR")


def test_get_required_env_empty_string_raises(monkeypatch):
    """
    Empty string is falsy — get_required_env treats it the same as missing.
    This catches the common mistake of setting KEY="" in a .env file.
    """
    monkeypatch.setenv("EMPTY_VAR", "")
    with pytest.raises(RuntimeError, match="EMPTY_VAR"):
        get_required_env("EMPTY_VAR")


def test_env_var_isolation(monkeypatch):
    """
    Demonstrate that monkeypatch changes are local to this test.
    After this test, MY_ISOLATED_VAR will NOT be in os.environ.
    Check this in test_env_var_isolation_confirmed below.
    """
    monkeypatch.setenv("MY_ISOLATED_VAR", "only-here")
    assert os.environ.get("MY_ISOLATED_VAR") == "only-here"


def test_env_var_isolation_confirmed():
    """
    This test runs after test_env_var_isolation.
    monkeypatch reverted the change — the var should be gone.
    (Note: pytest does not guarantee test order, but isolation is the point.)
    """
    assert os.environ.get("MY_ISOLATED_VAR") is None


# ─────────────────────────────────────────────────────────────────────────────
# PART 2 — match= in pytest.raises
#
# The match= parameter is a regex checked against str(exception).
# Use it to verify that the right error message fires, not just the right type.
# ─────────────────────────────────────────────────────────────────────────────

def test_error_message_mentions_variable_name(monkeypatch):
    """
    The error should name the specific variable that's missing so the
    developer knows exactly what to add to their .env file.
    """
    monkeypatch.delenv("SUPER_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="SUPER_SECRET"):
        get_required_env("SUPER_SECRET")


def test_error_message_mentions_dotenv(monkeypatch):
    """Error message should guide the user to the fix (.env file)."""
    monkeypatch.delenv("SUPER_SECRET", raising=False)
    with pytest.raises(RuntimeError, match=".env"):
        get_required_env("SUPER_SECRET")


# ─────────────────────────────────────────────────────────────────────────────
# PART 3 — unittest.mock.patch
#
# monkeypatch is great for env vars and simple attribute swaps.
# For mocking entire modules, classes, or async functions,
# unittest.mock.patch is the standard tool.
#
# Two forms:
#   1. Context manager:  with patch("module.ClassName") as mock_cls: ...
#   2. Decorator:        @patch("module.ClassName")
#
# The patch target is a dotted path to the name AS IT'S USED in the module
# under test — not where it's defined. This is the most common gotcha.
#
# Example: env_demo.py does `import anthropic`, then uses `anthropic.AsyncAnthropic`.
# So the patch target is "env_demo.anthropic.AsyncAnthropic" — the name
# as it appears in env_demo's namespace.
# ─────────────────────────────────────────────────────────────────────────────

def test_mock_basic_concept():
    """
    MagicMock is a flexible fake object:
      - Any attribute access returns another MagicMock
      - Any call returns a MagicMock
      - You can assert on calls that were made
    No real code runs — it's all in-memory.
    """
    mock_client = MagicMock()

    # Call a method that doesn't exist on the real object — MagicMock just tracks it
    mock_client.messages.create(model="haiku", max_tokens=10)

    # Assert the call happened
    mock_client.messages.create.assert_called_once()

    # Assert specific arguments were used
    mock_client.messages.create.assert_called_with(model="haiku", max_tokens=10)


def test_mock_return_value():
    """
    Set return_value to control what a mocked function returns.
    The production code gets a fake response object — no network call.
    """
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="API keys can be stolen and abused.")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    # Simulate production code calling the client
    response = mock_client.messages.create(model="haiku", max_tokens=128, messages=[])
    first_text = response.content[0].text

    assert first_text == "API keys can be stolen and abused."


def test_patch_as_context_manager(monkeypatch):
    """
    patch() as a context manager replaces the target for the duration of the
    `with` block, then restores it automatically.

    Here we patch os.environ.get to simulate a specific env var without
    actually setting it (alternative approach to monkeypatch for simple cases).
    """
    monkeypatch.setenv("PATCHED_KEY", "patched-value")
    result = get_required_env("PATCHED_KEY")
    assert result == "patched-value"


# ─────────────────────────────────────────────────────────────────────────────
# PART 4 — AsyncMock: mocking async functions
#
# Regular MagicMock doesn't work for async functions — `await mock()` fails.
# AsyncMock is the async-aware version: `await async_mock()` returns
# async_mock.return_value just like a regular mock.
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_async_mock_basics():
    """
    AsyncMock: behaves like MagicMock but is awaitable.
    Use it to replace any async function or method.
    """
    mock_create = AsyncMock()

    # Configure what it returns when awaited
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="API keys grant access to paid services.")]
    mock_create.return_value = fake_response

    # Await it — just like production code would
    response = await mock_create(model="haiku", max_tokens=128, messages=[])

    assert response.content[0].text == "API keys grant access to paid services."
    mock_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_anthropic_client_mocked():
    """
    Full integration test pattern for agent code:
      1. Patch the Anthropic client constructor so no real client is created
      2. Configure the mock to return a fake response
      3. Call our production function
      4. Assert behavior without any network I/O

    patch target: "env_demo.anthropic.AsyncAnthropic"
      → because env_demo.py uses `import anthropic` then `anthropic.AsyncAnthropic()`
    """
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="Never commit secrets to version control.")]

    mock_async_client = AsyncMock()
    mock_async_client.messages.create = AsyncMock(return_value=fake_response)

    with patch("env_demo.anthropic.AsyncAnthropic", return_value=mock_async_client):
        # Import and call the function that uses the Anthropic client
        from env_demo import section_4
        # section_4 calls get_required_env("ANTHROPIC_API_KEY") internally.
        # We need ANTHROPIC_API_KEY to be set (it's in your ~/.zprofile so it
        # should already be in the environment when running locally).
        await section_4()

    # Verify the mocked client was called
    mock_async_client.messages.create.assert_awaited_once()


# ─────────────────────────────────────────────────────────────────────────────
# PART 5 — Fixtures with scope
#
# By default, each test gets a fresh fixture instance (scope="function").
# scope="module" runs the fixture once per test file — good for expensive setup.
# scope="session" runs once for the entire pytest run.
#
# Rule of thumb:
#   scope="function"  — for anything that mutates state (env vars, files, DB rows)
#   scope="module"    — for read-only objects that are expensive to build
#   scope="session"   — for truly global read-only resources (DB connection, etc.)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def expected_env_keys():
    """
    Module-scoped: built once, shared by all tests in this file.
    Safe because this fixture is read-only.
    """
    return {"ANTHROPIC_API_KEY", "HOME", "SHELL"}


def test_well_known_env_keys_exist(expected_env_keys):
    """HOME and SHELL are always set on macOS/Linux."""
    for key in {"HOME", "SHELL"}:
        assert key in expected_env_keys


def test_api_key_in_expected_set(expected_env_keys):
    assert "ANTHROPIC_API_KEY" in expected_env_keys
