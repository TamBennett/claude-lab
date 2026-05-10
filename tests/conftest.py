"""
conftest.py — pytest configuration and shared fixtures.

pytest automatically discovers and loads this file before running tests.
Fixtures defined here are available to ALL test files in this directory
without any import. This is where project-wide fixtures live.

Key pytest configuration lives here too (via pytest_configure or pytest.ini).
"""

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# asyncio mode configuration
#
# pytest-asyncio requires knowing how to handle async test functions.
# The asyncio_mode="auto" setting means any async def test_* is automatically
# treated as an async test — no need to decorate each one with @pytest.mark.asyncio.
#
# We use "strict" here instead: you explicitly mark async tests.
# This makes it obvious which tests are async vs. sync.
# ─────────────────────────────────────────────────────────────────────────────

def pytest_configure(config):
    """Register custom markers so pytest doesn't warn about unknown marks."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async (requires pytest-asyncio)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow-running (skip with -m 'not slow')"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def anthropic_api_key(pytestconfig):
    """
    Session-scoped: resolved once per test run.

    Returns the API key from the environment. Tests that need a REAL
    Anthropic call use this fixture. Tests that mock the client don't need it.

    Usage in a test:
        def test_real_call(anthropic_api_key):
            client = anthropic.Anthropic(api_key=anthropic_api_key)
            ...
    """
    import os
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        pytest.skip("ANTHROPIC_API_KEY not set — skipping live API test")
    return key
