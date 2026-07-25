"""Day 1: one API call through OpenRouter.

Goal is not the generated code -- it is seeing where every cost number in the
thesis comes from. Two of those numbers are easy to get wrong, so this script
prints them explicitly:

  * reasoning tokens are billed but usually absent from the visible text, so
    measuring cost from response length understates it by 5-10x
  * the /generation endpoint reports what was *actually* charged, which is the
    ground truth when it disagrees with our own price-table arithmetic

Run:  uv run python scripts/day1_hello.py
"""

import os
import sys
import time

import httpx
from dotenv import load_dotenv
from openai import OpenAI

BASE_URL = "https://openrouter.ai/api/v1"

# Day 1 only. From Day 5 the roster lives in config/models.yaml, verified
# against OpenRouter's live /models endpoint -- never hardcoded.
MODEL = "qwen/qwen3-8b"

PROMPT = "Write a Python function that reverses a string. Return only the code."


def main() -> int:
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("OPENROUTER_API_KEY is not set. Copy .env.example to .env and add your key.")
        return 1

    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    started = time.perf_counter()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0,
    )
    latency_ms = (time.perf_counter() - started) * 1000

    print("=" * 70)
    print("RESPONSE TEXT")
    print("=" * 70)
    print(response.choices[0].message.content)

    usage = response.usage
    details = getattr(usage, "completion_tokens_details", None)
    # Absent on non-reasoning models, and on reasoning models these tokens are
    # billed without appearing in the text above.
    reasoning_tokens = getattr(details, "reasoning_tokens", None)

    print()
    print("=" * 70)
    print("USAGE  <- every cost number in the thesis is derived from this")
    print("=" * 70)
    print(f"  prompt_tokens      {usage.prompt_tokens}")
    print(f"  completion_tokens  {usage.completion_tokens}")
    print(f"  reasoning_tokens   {reasoning_tokens}")
    print(f"  latency_ms         {latency_ms:.0f}")

    # Ground truth for what this call cost. Our own price-table arithmetic gets
    # stored alongside this, and when the two disagree the API is right.
    print()
    print("=" * 70)
    print("ACTUAL CHARGE  (GET /generation)")
    print("=" * 70)
    try:
        # The generation record is written asynchronously and lags the response.
        time.sleep(2)
        charge = httpx.get(
            f"{BASE_URL}/generation",
            params={"id": response.id},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        charge.raise_for_status()
        data = charge.json().get("data", {})
        print(f"  total_cost (USD)   {data.get('total_cost')}")
        print(f"  native prompt tok  {data.get('native_tokens_prompt')}")
        print(f"  native compl. tok  {data.get('native_tokens_completion')}")
        print(f"  reasoning tok      {data.get('native_tokens_reasoning')}")
    except Exception as exc:  # noqa: BLE001 - Day 1 probe; failure is informative
        print(f"  lookup failed: {exc}")
        print("  (Not fatal. Note whether this endpoint is reliable -- if not,")
        print("   cost accounting falls back to the price table alone.)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
