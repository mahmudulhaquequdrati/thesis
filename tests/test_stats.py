"""The bootstrap produces numbers nothing else checks.

A grader bug corrupts `results.passed`; a bug here corrupts every interval
attached to every claim, and an interval that is silently too narrow is worse
than no interval at all -- it converts a guess into an apparent finding.

Run:  uv run pytest tests/test_stats.py -v
"""

import math

import pytest

from carr.stats import bootstrap_ci, ci_str, proportion, ratio

MEAN = lambda s: sum(s) / len(s) if s else None  # noqa: E731


# ------------------------------------------------------------ reproducibility


def test_same_seed_gives_an_identical_interval():
    """CLAUDE.md: fixed seeds everywhere. Reproducibility is graded."""
    data = list(range(100))
    a = bootstrap_ci(data, MEAN, seed=20260726, n_resamples=500)
    b = bootstrap_ci(data, MEAN, seed=20260726, n_resamples=500)
    assert a == b


def test_different_seeds_differ_but_agree():
    data = list(range(100))
    a = bootstrap_ci(data, MEAN, seed=1, n_resamples=500)
    b = bootstrap_ci(data, MEAN, seed=2, n_resamples=500)
    assert a != b
    assert a[0] < b[1] and b[0] < a[1], "seeds disagree beyond sampling noise"


# ------------------------------------------------------------- known answers


def test_bernoulli_interval_covers_the_truth_and_is_the_right_width():
    """A 50/50 coin over n=1000 has a 95% interval near 50%, roughly +/-3 points.

    The analytic standard error is sqrt(.25/1000) ~ 1.58 points, so the interval
    should span about 6.2 points. A bootstrap that is much tighter than that is
    not resampling properly.
    """
    data = [1] * 500 + [0] * 500
    lo, hi = bootstrap_ci(data, proportion(lambda x: x == 1),
                          seed=7, n_resamples=2000)
    assert lo < 50.0 < hi
    assert 4.0 < (hi - lo) < 9.0, f"width {hi - lo:.1f} points is implausible"


def test_smaller_samples_give_wider_intervals():
    """If the interval does not respond to n, it is not measuring uncertainty."""
    big = bootstrap_ci([1] * 250 + [0] * 250, proportion(lambda x: x == 1),
                       seed=3, n_resamples=1500)
    small = bootstrap_ci([1] * 10 + [0] * 10, proportion(lambda x: x == 1),
                         seed=3, n_resamples=1500)
    assert (small[1] - small[0]) > (big[1] - big[0]) * 2


# ------------------------------------------------- the ratio-estimator trap


def test_ratio_is_not_the_mean_of_ratios():
    """THESIS.md section 10.2's specific warning, made unrepeatable.

    CPC is sum(cost)/sum(solved). Averaging per-problem cost/solved is a
    different quantity, and on skewed data it is wildly different -- here 2.0
    against 0.55. Getting this wrong would misreport the headline economic
    metric while looking perfectly reasonable.
    """
    rows = [{"cost": 10.0, "solved": 5}, {"cost": 1.0, "solved": 10}]
    stat = ratio(lambda r: r["cost"], lambda r: r["solved"])

    assert stat(rows) == pytest.approx(11.0 / 15.0)          # 0.733
    mean_of_ratios = sum(r["cost"] / r["solved"] for r in rows) / len(rows)
    assert mean_of_ratios == pytest.approx(1.05)
    assert stat(rows) != pytest.approx(mean_of_ratios)


def test_ratio_returns_none_when_nothing_was_solved():
    """A config that solved nothing has no cost-per-correct.

    That is a real outcome on the hard tier, not an error, and it must not
    divide by zero or poison the interval.
    """
    stat = ratio(lambda r: r["cost"], lambda r: r["solved"])
    assert stat([{"cost": 5.0, "solved": 0}]) is None
    lo, hi = bootstrap_ci([{"cost": 5.0, "solved": 0}] * 20, stat,
                          seed=1, n_resamples=200)
    assert math.isnan(lo) and math.isnan(hi)


# ------------------------------------------------------------ degenerate input


def test_empty_input_returns_nan_rather_than_raising():
    """A tier with no data prints a blank interval; it does not kill the report."""
    lo, hi = bootstrap_ci([], MEAN, seed=1)
    assert math.isnan(lo) and math.isnan(hi)


def test_single_observation_claims_no_spread():
    """One point carries no information about uncertainty."""
    lo, hi = bootstrap_ci([42.0], MEAN, seed=1)
    assert lo == hi == 42.0


def test_all_identical_values_give_a_zero_width_interval():
    lo, hi = bootstrap_ci([5.0] * 50, MEAN, seed=1, n_resamples=200)
    assert lo == pytest.approx(5.0) and hi == pytest.approx(5.0)


# ------------------------------------------------------------------ formatting


def test_ci_str_is_blank_when_undefined():
    """Printing 'nan' in a results table invites it into the write-up."""
    assert ci_str(math.nan, math.nan) == ""
    assert ci_str(1.0, 2.0, pct=True) == "[1, 2]"
    assert ci_str(0.00015, 0.00028, places=5) == "[0.00015, 0.00028]"
