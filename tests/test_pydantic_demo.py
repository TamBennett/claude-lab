"""
M2.6 — Testing with pytest: unit tests, fixtures, mocking
Test file: test_pydantic_demo.py

Covers:
  1. Basic test functions — the simplest unit test shape
  2. pytest.raises — asserting that exceptions fire
  3. Fixtures — reusable setup shared across tests
  4. parametrize — data-driven tests, one function / many inputs
  5. Schema structure assertions — validating what Claude would receive

Run from your claude-lab root (with venv activated):
  pytest tests/test_pydantic_demo.py -v
"""

import json
import sys
import os

import pytest
from pydantic import ValidationError

# ── make the project root importable when running from claude-lab ──
# In a real project, `pip install -e .` or pyproject.toml handles this.
# For our flat scripts/ layout, we add the parent dir manually.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

# Import the classes we want to test directly from the demo module.
# This is the standard pattern: import the production code, test its behavior.
from pydantic_demo import UserProfile, SearchFilesInput, build_tool_schema


# ─────────────────────────────────────────────────────────────────────────────
# PART 1 — Basic test functions
#
# A test function in pytest:
#   • starts with `test_`
#   • lives in a file named `test_*.py`
#   • uses plain `assert` — pytest rewrites it with rich failure messages
#   • no return value — a test passes if it doesn't raise, fails if it raises
# ─────────────────────────────────────────────────────────────────────────────

def test_valid_user_profile_all_fields():
    """Happy path: all fields valid, correct values stored."""
    user = UserProfile(name="Tam", age=68, email="tam@example.com", role="admin")
    assert user.name == "Tam"
    assert user.age == 68
    assert user.email == "tam@example.com"
    assert user.role == "admin"


def test_valid_user_profile_defaults():
    """Omitting optional fields uses the declared defaults."""
    user = UserProfile(name="Alice", age=35)
    assert user.email is None          # default
    assert user.role == "viewer"       # default


def test_age_coercion_from_string():
    """
    Pydantic coerces compatible types — "42" → 42.
    This is deliberate Pydantic behavior; we test it so the contract is explicit.
    """
    user = UserProfile(name="Bob", age="42")
    assert user.age == 42
    assert isinstance(user.age, int)   # confirm it's actually an int, not a string


# ─────────────────────────────────────────────────────────────────────────────
# PART 2 — pytest.raises
#
# Use `with pytest.raises(SomeException):` to assert that code raises.
# The block passes if the exception fires; it fails if nothing is raised
# (or if a *different* exception fires, which propagates normally).
# ─────────────────────────────────────────────────────────────────────────────

def test_invalid_age_non_numeric_raises():
    """Non-numeric string cannot be coerced — Pydantic raises ValidationError."""
    with pytest.raises(ValidationError):
        UserProfile(name="Bad", age="not-a-number")


def test_invalid_role_raises():
    """Role must be one of the Literal values — any other string raises."""
    with pytest.raises(ValidationError):
        UserProfile(name="Bad", age=25, role="superuser")


def test_missing_required_field_raises():
    """name and age are required (no default) — omitting them raises."""
    with pytest.raises(ValidationError):
        UserProfile(age=30)           # name missing


def test_raises_can_inspect_the_exception():
    """
    Assign the exception info to a variable with `as exc_info`.
    Then check exc_info.value for the actual exception object.
    Useful when you need to verify error message content.
    """
    with pytest.raises(ValidationError) as exc_info:
        UserProfile(name="Bad", age=25, role="superuser")

    # exc_info.value is the actual ValidationError instance
    errors = exc_info.value.errors()
    assert len(errors) >= 1
    # The field that failed should be "role"
    assert errors[0]["loc"] == ("role",)


# ─────────────────────────────────────────────────────────────────────────────
# PART 3 — Fixtures
#
# A fixture is a function decorated with @pytest.fixture.
# pytest injects it by matching the parameter name in test functions.
# Fixtures handle setup (and optionally teardown via yield).
#
# Why use fixtures instead of just calling the constructor in every test?
#   • DRY — change the setup in one place
#   • Named clearly — the fixture name documents what the test needs
#   • Scoped — can be shared per-function, per-module, or per-session
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def admin_user():
    """Return a pre-built admin UserProfile for tests that need one."""
    return UserProfile(name="Tam", age=68, email="tam@example.com", role="admin")


@pytest.fixture
def viewer_user():
    """Return a pre-built viewer UserProfile (all defaults)."""
    return UserProfile(name="Alice", age=35)


def test_admin_user_role(admin_user):
    """Fixture injected by name — pytest calls admin_user() and passes the result."""
    assert admin_user.role == "admin"


def test_viewer_user_defaults(viewer_user):
    assert viewer_user.role == "viewer"
    assert viewer_user.email is None


def test_model_dump_contains_all_fields(admin_user):
    """
    model_dump() returns a dict — useful for serialization and assertions.
    We confirm that all expected keys are present and values are correct.
    """
    data = admin_user.model_dump()
    assert data == {
        "name": "Tam",
        "age": 68,
        "email": "tam@example.com",
        "role": "admin",
    }


# ─────────────────────────────────────────────────────────────────────────────
# PART 4 — parametrize
#
# @pytest.mark.parametrize runs one test function with multiple input sets.
# Each tuple becomes a separate test case in the output.
# This is the cleanest way to cover edge cases without duplicating test logic.
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role", ["admin", "viewer", "editor"])
def test_all_valid_roles_accepted(role):
    """Each Literal value should be accepted without error."""
    user = UserProfile(name="Test", age=30, role=role)
    assert user.role == role


@pytest.mark.parametrize("bad_role", ["superuser", "owner", "", "ADMIN", "Admin"])
def test_invalid_roles_all_raise(bad_role):
    """Every non-Literal value must raise — case-sensitive, no extras."""
    with pytest.raises(ValidationError):
        UserProfile(name="Test", age=30, role=bad_role)


@pytest.mark.parametrize("name,age,email,role", [
    ("Alice",   25,  "a@x.com",  "admin"),
    ("Bob",     40,  None,        "editor"),
    ("Charlie", 55,  "c@y.org",  "viewer"),
])
def test_multiple_valid_profiles(name, age, email, role):
    """Multi-field parametrize: one test row per tuple."""
    user = UserProfile(name=name, age=age, email=email, role=role)
    assert user.name == name
    assert user.age == age
    assert user.email == email
    assert user.role == role


# ─────────────────────────────────────────────────────────────────────────────
# PART 5 — Schema structure tests (SearchFilesInput + build_tool_schema)
#
# These verify what Claude actually receives as the tool's input_schema.
# Important for agent code: if the schema is malformed, Claude's tool call
# will either fail or produce incorrect inputs that pass validation by luck.
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def search_schema():
    """The JSON schema dict for SearchFilesInput."""
    return SearchFilesInput.model_json_schema()


def test_schema_has_required_fields(search_schema):
    """Pydantic marks fields without defaults as 'required'."""
    assert "required" in search_schema
    assert "query" in search_schema["required"]


def test_schema_optional_fields_not_required(search_schema):
    """Fields with defaults (max_results, include_archived) should NOT be required."""
    required = search_schema.get("required", [])
    assert "max_results" not in required
    assert "include_archived" not in required


def test_schema_field_types(search_schema):
    """Verify the JSON Schema type mapping for each field."""
    props = search_schema["properties"]
    assert props["query"]["type"] == "string"
    assert props["max_results"]["type"] == "integer"
    assert props["include_archived"]["type"] == "boolean"


def test_schema_numeric_constraints(search_schema):
    """Field(ge=1, le=100) should produce minimum/maximum in the schema."""
    props = search_schema["properties"]
    assert props["max_results"]["minimum"] == 1
    assert props["max_results"]["maximum"] == 100


def test_build_tool_schema_structure():
    """
    build_tool_schema() wraps a Pydantic model into a Claude tool definition.
    Verify the top-level shape Claude expects.
    """
    tool = build_tool_schema(
        name="search_files",
        description="Search files",
        model=SearchFilesInput,
    )
    assert tool["name"] == "search_files"
    assert tool["description"] == "Search files"
    assert "input_schema" in tool
    # input_schema must be a dict (the JSON Schema object)
    assert isinstance(tool["input_schema"], dict)
    assert "properties" in tool["input_schema"]
