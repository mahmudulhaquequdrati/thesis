"""Bootstrap confidence intervals. Stdlib only -- no numpy, no scipy.

THESIS.md section 10.2 asks for this by name, and gives the reason:

    CPC needs confidence intervals. Cost-per-correct is `sum(cost) / sum(correct)`
    -- a ratio estimator, therefore biased, and almost always reported bare.
    Bootstrap it so you never claim a frontier difference that's within noise.

It matters more here than usual. The abort curve's middle bands rest on ~58 and
~61 observations, and this project has already had one headline overturned: the
"free" 10,000-token threshold survived the pilot only because a 16k ceiling
truncated longer calls and forced them to fail. Point estimates at that sample
size are claims waiting to be withdrawn.

**The statistic receives the whole resample, not one item.** That is the entire
point for a ratio like CPC: it must be recomputed as sum(cost)/sum(solved) over
each resample. Averaging per-problem ratios estimates a different quantity and
is the specific mistake section 10.2 warns about -- see
tests/test_stats.py::test_ratio_is_not_the_mean_of_ratios.

Seeding is required, not optional (CLAUDE.md section 3): "Fixed seeds
everywhere -- sampling, splits, bootstrap. Reproducibility is a graded property
of a thesis."
"""

from __future__ import annotations

import math
import random
from typing import Callable, Sequence, TypeVar

T = TypeVar("T")

DEFAULT_RESAMPLES = 10_000
DEFAULT_CONFIDENCE = 0.95


def bootstrap_ci(items: Sequence[T],
                 statistic: Callable[[Sequence[T]], float | None],
                 *,
                 seed: int,
                 n_resamples: int = DEFAULT_RESAMPLES,
                 confidence: float = DEFAULT_CONFIDENCE) -> tuple[float, float]:
    """Percentile bootstrap interval for `statistic` over `items`.

    `items` are the independent units being resampled -- for this project that
    is always PROBLEMS, never individual cells, because two cells on the same
    problem are not independent observations of difficulty.

    Returns (nan, nan) when there is nothing to resample, so a tier with no data
    prints a blank interval instead of aborting the whole report.
    """
    n = len(items)
    if n == 0:
        return (math.nan, math.nan)
    if n == 1:
        # One observation carries no information about spread. Say so with a
        # degenerate interval rather than implying precision that is not there.
        value = statistic(items)
        return (math.nan, math.nan) if value is None else (value, value)

    rng = random.Random(seed)
    values: list[float] = []
    for _ in range(n_resamples):
        resample = [items[rng.randrange(n)] for _ in range(n)]
        value = statistic(resample)
        if value is not None:
            values.append(value)

    if not values:
        return (math.nan, math.nan)

    values.sort()
    alpha = (1.0 - confidence) / 2.0
    return (_percentile(values, alpha), _percentile(values, 1.0 - alpha))


def _percentile(sorted_values: list[float], q: float) -> float:
    """Linear-interpolated percentile of an already-sorted list."""
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = pos - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def ratio(numerator: Callable[[T], float],
          denominator: Callable[[T], float]) -> Callable[[Sequence[T]], float | None]:
    """A ratio-of-sums statistic, which is what CPC and TPC are.

    Returns None when the denominator is zero -- a config that solved nothing
    has no cost-per-correct, and that is a real outcome on the hard tier rather
    than an error. bootstrap_ci drops those resamples.
    """
    def stat(sample: Sequence[T]) -> float | None:
        den = sum(denominator(x) for x in sample)
        if den <= 0:
            return None
        return sum(numerator(x) for x in sample) / den
    return stat


def proportion(predicate: Callable[[T], bool]) -> Callable[[Sequence[T]], float | None]:
    """Percentage of the sample satisfying `predicate`. For pass rates."""
    def stat(sample: Sequence[T]) -> float | None:
        if not sample:
            return None
        return 100.0 * sum(1 for x in sample if predicate(x)) / len(sample)
    return stat


def ci_str(lo: float, hi: float, *, pct: bool = False, places: int = 4) -> str:
    """Consistent rendering, and blank rather than 'nan' when undefined."""
    if math.isnan(lo) or math.isnan(hi):
        return ""
    if pct:
        return f"[{lo:.0f}, {hi:.0f}]"
    return f"[{lo:.{places}f}, {hi:.{places}f}]"
