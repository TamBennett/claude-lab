"""
M2.3 — Async Python: asyncio, async/await, event loops
Exercises for claude-lab/scripts/async_demo.py

Run each section individually by commenting/uncommenting the asyncio.run() call at the bottom,
or run the full demo in order.
"""

import asyncio
import time
import anthropic


# ─────────────────────────────────────────────
# EXAMPLE 1 — Basic coroutine
# Key point: calling an async def does NOT execute it.
#             await (or asyncio.run) actually runs it.
# ─────────────────────────────────────────────

async def greet(name: str) -> str:
    return f"Hello, {name}"


async def example_1():
    print("=== Example 1: Basic coroutine ===")

    # This creates a coroutine object — does NOT run it:
    coro = greet("Tam")
    print(f"  coro before await: {coro}")   # <coroutine object greet at 0x...>

    # This runs it:
    result = await coro
    print(f"  result after await: {result}")


# ─────────────────────────────────────────────
# EXAMPLE 2 — Simulated I/O delay, sequential
# Key point: sequential awaits run one at a time.
#             Total time = sum of all delays.
# ─────────────────────────────────────────────

async def slow_call(label: str, delay: float) -> str:
    print(f"  {label}: starting")
    await asyncio.sleep(delay)      # non-blocking — only suspends THIS coroutine
    print(f"  {label}: done")
    return f"{label} result"


async def example_2():
    print("\n=== Example 2: Sequential awaits ===")
    start = time.perf_counter()

    r1 = await slow_call("A", 1.0)
    r2 = await slow_call("B", 1.0)

    elapsed = time.perf_counter() - start
    print(f"  Results: {r1}, {r2}")
    print(f"  Elapsed: {elapsed:.2f}s  (expected ~2.0s — sum of delays)")


# ─────────────────────────────────────────────
# EXAMPLE 3 — asyncio.gather() parallel execution
# Key point: gather() launches coroutines concurrently.
#             Total time ≈ max(delays), not sum.
# ─────────────────────────────────────────────

async def example_3():
    print("\n=== Example 3: Parallel with asyncio.gather() ===")
    start = time.perf_counter()

    # Both run concurrently — event loop context-switches between them at each await
    r1, r2 = await asyncio.gather(
        slow_call("A", 1.0),
        slow_call("B", 1.0),
    )

    elapsed = time.perf_counter() - start
    print(f"  Results: {r1}, {r2}")
    print(f"  Elapsed: {elapsed:.2f}s  (expected ~1.0s — max of delays)")


# ─────────────────────────────────────────────
# EXAMPLE 4 — Real AsyncAnthropic SDK call
# Key point: AsyncAnthropic is the async client.
#             Use it with await just like any other coroutine.
# ─────────────────────────────────────────────

async def ask_claude(question: str) -> str:
    client = anthropic.AsyncAnthropic()     # async client — not Anthropic()
    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{"role": "user", "content": question}],
    )
    return message.content[0].text


async def example_4():
    print("\n=== Example 4: Real async Claude SDK call ===")
    answer = await ask_claude("What is asyncio in one sentence?")
    print(f"  Claude says: {answer}")


# ─────────────────────────────────────────────
# BONUS — Parallel Claude calls with gather()
# This is the real-world pattern for multi-agent work:
# fire off multiple LLM calls concurrently, collect all results.
# ─────────────────────────────────────────────

async def example_bonus():
    print("\n=== Bonus: Two Claude calls in parallel ===")
    start = time.perf_counter()

    q1 = "What is asyncio in one sentence?"
    q2 = "What is the event loop in one sentence?"

    a1, a2 = await asyncio.gather(
        ask_claude(q1),
        ask_claude(q2),
    )

    elapsed = time.perf_counter() - start
    print(f"  Q1: {a1}")
    print(f"  Q2: {a2}")
    print(f"  Elapsed: {elapsed:.2f}s")


# ─────────────────────────────────────────────
# MAIN — run all examples in order
# Comment out any example_N() call to skip it.
# ─────────────────────────────────────────────

async def main():
    await example_1()
    await example_2()
    await example_3()
    await example_4()
    await example_bonus()


if __name__ == "__main__":
    asyncio.run(main())
