"""The real backend. Every call through here costs money.

Implements the Provider contract in base.py against OpenRouter, which is
OpenAI-compatible -- so the `openai` SDK works with `base_url` swapped and no
custom HTTP client.

The send contract is docs/data-spec.md section 2, and it is deliberately
minimal: the benchmark prompt goes as a single user message, unmodified. No
system prompt, no "you are an expert programmer", no "think step by step".
Any of those would change token counts and confound the effort axis, which is
the one variable under study.

Four things this file exists to get right:

1. `reasoning_tokens` lives in usage.completion_tokens_details and is billed
   while being invisible in the response text. Day 1 measured 392 of 412 on
   "reverse a string". Missing it understates cost ~20x.
2. The `reasoning` block comes verbatim from config/models.yaml. It is the
   entire experimental manipulation; nothing here may invent it.
3. `max_tokens` is a cost control, not a quality setting. A truncated answer is
   a legitimate failure that cost a known, bounded amount.
4. Errors are returned as a Generation with `.error` set, never raised. A grid
   run that aborts on one 502 is a grid run that wastes everything before it.

Cost is NOT reconciled here. GET /generation needs ~10s to settle, so the
runner collects `provider_gen_id` and reconciles in a batch afterwards --
blocking per call would add hours.
"""

from __future__ import annotations

import json
import os
import time

from carr.providers.base import Generation, Usage

BASE_URL = "https://openrouter.ai/api/v1"

# Per-call ceiling on completion tokens (docs/data-spec.md section 2). One
# runaway reasoning trace can cost more than a hundred normal calls.
DEFAULT_MAX_TOKENS = 16000


class OpenRouterProvider:
    """Real generations. Construct once, reuse -- the client pools connections."""

    name = "openrouter"

    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL,
                 timeout: float = 300.0):
        key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Put it in .env (gitignored) "
                "and load it with python-dotenv, or pass api_key=."
            )
        from openai import OpenAI

        self._key = key
        self._base_url = base_url
        self._client = OpenAI(api_key=key, base_url=base_url, timeout=timeout)

    def fetch_cost(self, generation_id: str) -> float | None:
        """Ground-truth `total_cost` for one generation, or None if unavailable.

        Free -- this is a lookup, not a generation. Returns None rather than
        raising: the record 404s until it settles (~10s), and a missing cost is
        a reconciliation gap, not a reason to lose a run. `cost_computed_usd`
        remains the fallback.

        Not in the OpenAI schema, so it is a plain GET rather than an SDK call.
        """
        import urllib.error
        import urllib.request

        req = urllib.request.Request(
            f"{self._base_url}/generation?id={generation_id}",
            headers={"Authorization": f"Bearer {self._key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read()).get("data") or {}
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            return None
        cost = data.get("total_cost")
        return float(cost) if cost is not None else None

    def complete(self, prompt: str, config, *, problem_id: str,
                 max_tokens: int = DEFAULT_MAX_TOKENS,
                 temperature: float = 0.0) -> Generation:
        """One paid API call. `problem_id` is unused here; see base.Provider."""
        started = time.perf_counter()
        try:
            resp = self._client.chat.completions.create(
                model=config.model_slug,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                # The reasoning block is not an OpenAI parameter, so it rides in
                # extra_body. Straight from the roster -- never constructed here.
                extra_body=dict(config.params),
            )
        except Exception as exc:
            # Includes rate limits, timeouts and upstream 5xx. The row records
            # the failure and the loop moves on.
            return Generation(
                error=f"{type(exc).__name__}: {exc}",
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        choice = resp.choices[0] if resp.choices else None
        text = getattr(choice.message, "content", None) if choice else None

        u = getattr(resp, "usage", None)
        usage = None
        if u is not None:
            details = getattr(u, "completion_tokens_details", None)
            # Absent on non-reasoning models and on reasoning-off calls.
            reasoning = getattr(details, "reasoning_tokens", None) or 0
            usage = Usage(
                prompt_tokens=getattr(u, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(u, "completion_tokens", 0) or 0,
                reasoning_tokens=reasoning,
            )

        # A thinking model can spend its whole budget reasoning and return no
        # text at all. That is a real, paid, empty result -- record it as one
        # rather than letting it look like a transport failure.
        error = None
        if not text:
            error = "empty response (no content returned)"

        return Generation(
            raw_response=text,
            usage=usage,
            finish_reason=getattr(choice, "finish_reason", None) if choice else None,
            latency_ms=latency_ms,
            error=error,
            provider_gen_id=getattr(resp, "id", None),
        )
