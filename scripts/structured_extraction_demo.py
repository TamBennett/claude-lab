"""
M6.4 — Prompt Engineering & Structured Output (CCA-F exam domain, 20%)
structured_extraction_demo.py — the full thread, end to end:

  1. Define ONE "tool" that's really just a schema (fake tool trick)
  2. Force Claude to use it with tool_choice
  3. Make it bulletproof with Structured Outputs (strict: true)
  4. Validate what strict mode can't check (business rules) + retry loop
  5. Second pass: a separate Claude call reviews the extraction (evaluator-optimizer)

Scenario: extract structured data from a customer support email.
Run: python structured_extraction_demo.py
"""

import json
from typing import Literal

import anthropic
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

MODEL = "claude-haiku-4-5-20251001"   # cheap model is fine for extraction + review

client = anthropic.Anthropic()


# ─────────────────────────────────────────────
# SAMPLE INPUT — the thing we're extracting structured data FROM
# ─────────────────────────────────────────────

SAMPLE_EMAIL = """\
Subject: Still can't log in after your last update!!

Hi, this is the third time this week my account has locked me out right after
your app update. I've reset my password twice already and nothing works.
I need this fixed today, I use this for my job. - Priya Shah
"""


# ─────────────────────────────────────────────
# SECTION 1 — The schema (Pydantic model)
#
# This is the SAME model_json_schema() pattern from M2.4's pydantic_demo.py.
# Two things a JSON schema can't (fully) express on its own, both pushed
# into the field_validator instead:
#   1. Range: urgency must be 1-5. Structured Outputs' strict mode does NOT
#      support numeric constraints (minimum/maximum) in the schema at all —
#      Pydantic's `ge=1, le=5` would normally emit those keywords, and the
#      API rejects the tool outright if you leave them in. So the type stays
#      a bare `int` in the schema; the range check moves to Python.
#   2. Business rule: urgency 5 is only valid for technical issues — no
#      generic JSON schema keyword expresses "this field depends on that
#      field's value."
# Both are exactly what Structured Outputs CAN'T do for you — it guarantees
# SHAPE (is this an int), not RANGE or MEANING. That's what Section 5's
# retry loop is still responsible for.
# ─────────────────────────────────────────────

class CustomerIssue(BaseModel):
    # extra="forbid" is required for Structured Outputs' strict:true mode:
    # it makes model_json_schema() emit "additionalProperties": false, which
    # the constrained-decoding grammar compiler needs on every object schema.
    # Without it, model_json_schema() leaves the schema "open" and Claude's
    # API rejects the tool with a 400 (invalid_request_error).
    model_config = ConfigDict(extra="forbid")

    customer_name: str = Field(..., description="The customer's full name")
    issue_type: Literal["billing", "technical", "other"] = Field(
        ..., description="Category of the issue"
    )
    # NOTE: no ge=/le= here — see comment block above. Range is enforced in
    # the validator below, not in the schema.
    urgency: int = Field(
        ...,
        description=(
            "Severity on a 1-5 scale: 1 = minor inconvenience, 3 = affects "
            "normal use, 5 = business-critical / blocking (e.g. can't work, "
            "recurring outage). Range enforced by validator, not schema."
        ),
    )

    @field_validator("urgency")
    @classmethod
    def urgency_in_range_and_matches_issue_type(cls, v: int, info) -> int:
        if not (1 <= v <= 5):
            raise ValueError(f"urgency must be between 1 and 5, got {v}")
        issue_type = info.data.get("issue_type")
        if v == 5 and issue_type != "technical":
            raise ValueError(
                f"urgency=5 is only allowed when issue_type='technical' "
                f"(got issue_type='{issue_type}')"
            )
        return v


# ─────────────────────────────────────────────
# SECTION 2 — The fake tool
#
# We never execute this. Its only job is to give Claude a shape to fill in.
# Notice: this is the exact same build_tool_schema() pattern as M2.4/M4.3 —
# nothing new mechanically, just a new PURPOSE for the mechanism.
# ─────────────────────────────────────────────

def build_extraction_tool(strict: bool = False) -> dict:
    tool = {
        "name": "log_customer_issue",
        "description": (
            "Record a structured summary of a customer's support issue, "
            "extracted from their raw message. Not a real action — used "
            "purely to force structured output."
        ),
        "input_schema": CustomerIssue.model_json_schema(),
    }
    if strict:
        tool["strict"] = True   # Structured Outputs: guarantees schema conformance
    return tool


# ─────────────────────────────────────────────
# SECTION 3 — Classic pattern: forced tool_choice, no guarantees
#
# tool_choice = {"type": "tool", "name": ...} forces Claude to call THIS
# tool. Works everywhere, but the output shape is "very likely correct,"
# not "guaranteed correct."
# ─────────────────────────────────────────────

def extract_classic(email_text: str) -> dict:
    tool = build_extraction_tool(strict=False)

    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        tools=[tool],
        tool_choice={"type": "tool", "name": "log_customer_issue"},
        messages=[{
            "role": "user",
            "content": f"Extract the issue details from this email:\n\n{email_text}",
        }],
    )

    tool_block = next(b for b in response.content if b.type == "tool_use")
    return tool_block.input


# ─────────────────────────────────────────────
# SECTION 4 — Bulletproof pattern: Structured Outputs (strict mode)
#
# Same call shape, plus the beta header and strict: true on the tool.
# The API now restricts token generation so the shape CANNOT be wrong.
#
# NOTE: this beta header/model support is a moving target — verify current
# support at platform.claude.com/docs/en/build-with-claude/structured-outputs
# before relying on this in production. If unsupported, this call will 400
# and you fall back to Section 3 + a stricter retry loop.
# ─────────────────────────────────────────────

def extract_strict(email_text: str, messages: list[dict] | None = None) -> tuple[dict, str, list]:
    """Returns (validated_input_dict, tool_use_id, full_response_content)."""
    tool = build_extraction_tool(strict=True)

    if messages is None:
        messages = [{
            "role": "user",
            "content": f"Extract the issue details from this email:\n\n{email_text}",
        }]

    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        extra_headers={"anthropic-beta": "structured-outputs-2025-11-13"},
        tools=[tool],
        tool_choice={"type": "tool", "name": "log_customer_issue"},
        messages=messages,
    )

    tool_block = next(b for b in response.content if b.type == "tool_use")
    return tool_block.input, tool_block.id, response.content


# ─────────────────────────────────────────────
# SECTION 5 — Validation-retry loop
#
# Structured Outputs already guaranteed the SHAPE. This loop only has to
# catch what Section 1's field_validator catches: business-rule violations.
# On failure, we feed the error back to Claude as a tool_result with
# is_error=True — same tool_use_id matching pattern as your M4.3/M5.8 loop —
# and ask it to correct itself. Capped attempts, same idea as the tenacity
# pattern from M2.8, written out manually here so every step is visible.
# ─────────────────────────────────────────────

def extract_with_retry(email_text: str, max_attempts: int = 3) -> CustomerIssue:
    messages = [{
        "role": "user",
        "content": f"Extract the issue details from this email:\n\n{email_text}",
    }]

    for attempt in range(1, max_attempts + 1):
        raw_input, tool_use_id, response_content = extract_strict(email_text, messages)
        print(f"  [attempt {attempt}] raw extraction: {raw_input}")

        try:
            return CustomerIssue.model_validate(raw_input)
        except ValidationError as e:
            if attempt == max_attempts:
                raise
            print(f"  [attempt {attempt}] validation failed: {e}")

            # Feed the failed attempt + the error back to Claude as the next turn
            messages.append({"role": "assistant", "content": response_content})
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": f"Validation failed: {e}. Correct the values and call the tool again.",
                    "is_error": True,
                }],
            })

    raise RuntimeError("unreachable")   # loop always returns or raises above


# ─────────────────────────────────────────────
# SECTION 6 — Second-pass review (evaluator-optimizer / "multi-pass review")
#
# A SEPARATE Claude call, no tool involved — just asked to sanity-check the
# first pass's output against the source text. This is the same pattern as
# M6.2's evaluator-optimizer workflow, just applied to a prompt-engineering
# problem instead of an architecture problem.
#
# GOTCHA THIS CAUGHT: the reviewer is a fresh Claude call with no memory of
# Section 4's tool schema. Shown bare "urgency": 5 with no context, it has
# no way to know 5 is already the maximum — it guessed at a 1-10 scale and
# flagged a false mismatch. Fix: pull the field descriptions straight from
# CustomerIssue.model_json_schema() and hand them to the reviewer too, so
# both passes are grounded in the SAME definition of what each field means
# instead of the reviewer inventing its own assumption.
# ─────────────────────────────────────────────

def review_extraction(email_text: str, extracted: CustomerIssue) -> str:
    schema = CustomerIssue.model_json_schema()
    field_notes = "\n".join(
        f"- {name}: {info.get('description', '')}"
        for name, info in schema["properties"].items()
    )

    prompt = f"""Original email:
{email_text}

Field definitions (these define what each field means — use them, don't guess):
{field_notes}

Extracted data:
{extracted.model_dump_json(indent=2)}

Does the extracted data accurately reflect the email, given the field definitions above? Reply in exactly this format:
VERDICT: APPROVE or REVISE
REASON: <one sentence>"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ─────────────────────────────────────────────
# MAIN — run the full thread against SAMPLE_EMAIL
# ─────────────────────────────────────────────

def main() -> None:
    print("=== Step 1: classic forced tool_choice (no guarantees) ===")
    classic_result = extract_classic(SAMPLE_EMAIL)
    print(json.dumps(classic_result, indent=2))

    print("\n=== Step 2-4: Structured Outputs + validation-retry loop ===")
    validated = extract_with_retry(SAMPLE_EMAIL)
    print(f"\nValidated CustomerIssue: {validated}")

    print("\n=== Step 5: second-pass review ===")
    verdict = review_extraction(SAMPLE_EMAIL, validated)
    print(verdict)


if __name__ == "__main__":
    main()
