"""The contract every provider satisfies.

There are two implementations planned: `echo` (free, deterministic, offline)
and `openrouter` (Day 4, costs money). Everything downstream -- extraction,
grading, storage, both viewers -- works against `Generation` alone, so swapping
the mock for the real backend changes exactly one line in the runner.

`Generation` mirrors the fields OpenRouter actually returns, including the ones
that are easy to forget: `reasoning_tokens` (billed but invisible in the text)
and `finish_reason` (a 'length' response is truncated, not wrong).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class Usage:
    """Token counts as the API reports them.

    `reasoning_tokens` is a SUBSET of `completion_tokens`, not an addition to
    it. See carr/cost.py.
    """

    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int = 0

    @property
    def visible_tokens(self) -> int:
        """Completion tokens that actually appear in the response text."""
        return max(0, self.completion_tokens - self.reasoning_tokens)


@dataclass
class Generation:
    """One API response, successful or not."""

    raw_response: str | None = None
    usage: Usage | None = None
    finish_reason: str | None = None      # 'stop' | 'length'
    latency_ms: int = 0
    error: str | None = None              # non-None means no usable response
    provider_gen_id: str | None = None    # for batched cost reconciliation
    is_mock: bool = False
    mock_mode: str | None = None          # echo only; NULL for real rows


class Provider(Protocol):
    """What a backend must implement.

    `problem_id` is passed even though a real backend ignores it: the echo
    provider needs it to look up a problem, and keeping one signature means the
    runner does not branch on which provider it holds.
    """

    name: str

    def complete(self, prompt: str, config: Any, *, problem_id: str,
                 max_tokens: int = 4096, temperature: float = 0.0) -> Generation:
        ...
