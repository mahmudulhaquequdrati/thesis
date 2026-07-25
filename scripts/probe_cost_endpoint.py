"""Probe whether OpenRouter's /generation endpoint gives us ground-truth cost.

Cost accounting has two possible sources: our own price table times the token
counts, or the amount OpenRouter actually charged. The second is authoritative,
but only if the endpoint is reachable and settles quickly enough to poll after
each call. This decides which one cost.py can rely on.

Run:  uv run python scripts/probe_cost_endpoint.py
"""

import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv("/Users/mahmudqudrati/thesis/.env")
KEY = os.environ["OPENROUTER_API_KEY"]
HEADERS = {"Authorization": f"Bearer {KEY}"}

resp = httpx.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers=HEADERS,
    json={
        "model": "qwen/qwen3-8b",
        "messages": [{"role": "user", "content": "say hi"}],
        "max_tokens": 20,
    },
    timeout=60,
)
gen_id = resp.json()["id"]
print(f"gen id: {gen_id}")

# The generation record is written asynchronously, so a 404 right after the
# response only means "not settled yet". Back off before concluding anything.
for delay in (2, 3, 5, 10, 20):
    time.sleep(delay)
    got = httpx.get(
        "https://openrouter.ai/api/v1/generation",
        params={"id": gen_id},
        headers=HEADERS,
        timeout=30,
    )
    print(f"  +{delay}s -> HTTP {got.status_code}")
    if got.status_code == 200:
        data = got.json()["data"]
        print("\n  AVAILABLE FIELDS:", sorted(data.keys()))
        for field in (
            "total_cost",
            "native_tokens_prompt",
            "native_tokens_completion",
            "native_tokens_reasoning",
        ):
            print(f"  {field} = {data.get(field)}")
        break
else:
    print("\n  Never settled. cost.py must fall back to the price table alone,")
    print("  and the price table then needs verifying against the dashboard.")
