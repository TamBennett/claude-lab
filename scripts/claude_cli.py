#!/usr/bin/env python3
"""
claude_cli.py — minimal CLI tool that calls Claude directly via the Anthropic Python SDK.
Demonstrates: messages.create, streaming, and basic tool use.
"""
import argparse
import anthropic


def simple_call(client: anthropic.Anthropic, prompt: str, model: str) -> None:
    """Basic single-turn call — the foundation of everything."""
    print(f"\n--- Simple Call ---")
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    print(message.content[0].text)
    print(f"\n[Usage: input={message.usage.input_tokens} output={message.usage.output_tokens} tokens]")


def streaming_call(client: anthropic.Anthropic, prompt: str, model: str) -> None:
    """Streaming call — tokens arrive as they're generated."""
    print(f"\n--- Streaming Call ---")
    with client.messages.stream(
        model=model,
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
    print("\n")


def multi_turn_call(client: anthropic.Anthropic, model: str) -> None:
    """Multi-turn conversation — maintains message history manually."""
    print(f"\n--- Multi-turn Call ---")
    messages = []

    turns = [
        "My name is Tam. I'm building a Claude Code training program.",
        "What should my first module cover?",
        "Summarize what you know about me in one sentence."
    ]

    for turn in turns:
        print(f"\nUser: {turn}")
        messages.append({"role": "user", "content": turn})

        response = client.messages.create(
            model=model,
            max_tokens=512,
            messages=messages
        )

        assistant_text = response.content[0].text
        print(f"Claude: {assistant_text}")
        messages.append({"role": "assistant", "content": assistant_text})


def main():
    parser = argparse.ArgumentParser(description="Claude API CLI demo")
    parser.add_argument("--mode", choices=["simple", "stream", "multi"], default="simple")
    parser.add_argument("--prompt", default="Explain the MCP filesystem server in one paragraph.")
    parser.add_argument("--model", default="claude-haiku-4-5-20251001")
    args = parser.parse_args()

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

    if args.mode == "simple":
        simple_call(client, args.prompt, args.model)
    elif args.mode == "stream":
        streaming_call(client, args.prompt, args.model)
    elif args.mode == "multi":
        multi_turn_call(client, args.model)


if __name__ == "__main__":
    main()