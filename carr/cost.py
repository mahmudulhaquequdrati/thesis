"""Cost arithmetic. Prices are USD per million tokens, from config/models.yaml.

One rule, and getting it wrong silently corrupts every CPC number in the
thesis: **reasoning tokens are already inside `completion_tokens`.** OpenRouter
reports `usage.completion_tokens` as the billed total and breaks out
`completion_tokens_details.reasoning_tokens` as a subset of it. Adding the two
double-charges every thinking config, which would inflate exactly the configs
the thesis is about.

Day 1 measured the size of the effect from the other direction: a trivial
"reverse a string" prompt returned 412 completion tokens of which 392 were
reasoning, invisible in the response text. Pricing from visible text would have
understated that call ~20x.
"""

from __future__ import annotations


def compute_cost(prompt_tokens: int | None, completion_tokens: int | None,
                 price_in_per_m: float, price_out_per_m: float) -> float:
    """USD for one generation, from token counts and the price table.

    This is `cost_computed_usd`. It is an estimate; `cost_actual_usd` from
    OpenRouter's /generation endpoint is ground truth and wins wherever both
    exist. We keep both so drift between them is visible rather than assumed
    away -- a silent price change is otherwise undetectable.
    """
    p_in = (prompt_tokens or 0) * price_in_per_m
    p_out = (completion_tokens or 0) * price_out_per_m
    return (p_in + p_out) / 1e6


def fmt_usd(amount: float | None) -> str:
    """Money at a fixed 6dp -- single generations cost fractions of a cent."""
    if amount is None:
        return "-"
    return f"${amount:.6f}"
