"""
M2.4 — Type Hints and Pydantic: data validation for tool inputs/outputs
Exercises for claude-lab/scripts/pydantic_demo.py

Three sections:
  1. UserProfile model — valid/invalid data, Literal types, ValidationError
  2. model_json_schema() — see what Claude receives as a tool schema
  3. build_tool_schema + AsyncAnthropic — Claude calls a tool, Pydantic validates input
"""

import asyncio
import json
from typing import Literal

import anthropic
from pydantic import BaseModel, Field, ValidationError


# ─────────────────────────────────────────────
# SECTION 1 — UserProfile model
# Demonstrates: BaseModel, optional fields, Literal type constraints,
#               type coercion, and ValidationError on bad data.
# ─────────────────────────────────────────────

class UserProfile(BaseModel):
    name: str
    age: int
    email: str | None = None                              # optional — defaults to None
    role: Literal["admin", "viewer", "editor"] = "viewer" # constrained to 3 valid values


def section_1():
    print("=== Section 1: UserProfile model ===\n")

    # Valid — all fields provided
    u1 = UserProfile(name="Tam", age=68, email="tam@example.com", role="admin")
    print(f"Valid user:       {u1}")

    # Valid — optional email omitted, role defaults to "viewer"
    u2 = UserProfile(name="Alice", age=35)
    print(f"Defaults applied: {u2}")

    # Type coercion — age passed as string, Pydantic converts to int
    u3 = UserProfile(name="Bob", age="42")
    print(f"Coerced age:      {u3}  (age type: {type(u3.age).__name__})")

    # Invalid — age cannot be coerced from a non-numeric string
    print("\n--- ValidationError: bad age ---")
    try:
        UserProfile(name="Bad", age="not-a-number")
    except ValidationError as e:
        print(e)

    # Invalid — role is not in the Literal set
    print("\n--- ValidationError: bad role ---")
    try:
        UserProfile(name="Bad", age=25, role="superuser")
    except ValidationError as e:
        print(e)


# ─────────────────────────────────────────────
# SECTION 2 — model_json_schema()
# This is what Claude receives as the tool's input_schema.
# Note how Pydantic maps Python types → JSON Schema types,
# and how Field(description=...) becomes the "description" key.
# ─────────────────────────────────────────────

class SearchFilesInput(BaseModel):
    query: str = Field(..., description="The search query string")
    max_results: int = Field(10, ge=1, le=100, description="Max number of results to return")
    include_archived: bool = Field(False, description="Include archived files in results")


def section_2():
    print("\n=== Section 2: model_json_schema() ===\n")

    schema = SearchFilesInput.model_json_schema()
    print("SearchFilesInput schema (what Claude sees as input_schema):")
    print(json.dumps(schema, indent=2))

    print("\nUserProfile schema:")
    print(json.dumps(UserProfile.model_json_schema(), indent=2))


# ─────────────────────────────────────────────
# SECTION 3 — AsyncAnthropic + tool call + Pydantic validation
# Pattern: generate tool schema from Pydantic model → pass to Claude →
#          Claude returns tool_use block → validate input through Pydantic.
# ─────────────────────────────────────────────

def build_tool_schema(name: str, description: str, model: type[BaseModel]) -> dict:
    """Generate a Claude-compatible tool definition from a Pydantic model."""
    return {
        "name": name,
        "description": description,
        "input_schema": model.model_json_schema(),
    }


async def section_3() -> None:
    print("\n=== Section 3: Claude tool call + Pydantic validation ===\n")

    client = anthropic.AsyncAnthropic()

    tool_def = build_tool_schema(
        name="search_files",
        description="Search for files matching a query string",
        model=SearchFilesInput,
    )

    print(f"Tool sent to Claude: {tool_def['name']}")

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        tools=[tool_def],
        messages=[{
            "role": "user",
            "content": "Search for async Python files and return 3 results.",
        }],
    )

    print(f"Stop reason: {response.stop_reason}")  # expect "tool_use"

    for block in response.content:
        if block.type == "tool_use":
            print(f"\nClaude called tool: {block.name}")
            print(f"Raw input from Claude: {block.input}")

            # Validate Claude's tool call input through Pydantic
            params = SearchFilesInput.model_validate(block.input)
            print(f"\nValidated params:")
            print(f"  query:            {params.query}")
            print(f"  max_results:      {params.max_results}")
            print(f"  include_archived: {params.include_archived}")
            print(f"\nAs dict: {params.model_dump()}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

async def main() -> None:
    section_1()
    section_2()
    await section_3()


if __name__ == "__main__":
    asyncio.run(main())
