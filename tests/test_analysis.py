"""The analysis produces every number that goes in the thesis.

A grader bug corrupts `results.passed`; a bug in here corrupts the conclusions
drawn from it, which is worse because nothing downstream would notice. These
tests build a database with known answers and check the arithmetic against them.

Run:  uv run pytest tests/test_analysis.py -v
"""

import pytest

from carr import analysis, db
from carr.effort import load_configs
from carr.execute.verify import GradeResult


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "a.sqlite")
    db.init_schema(c)
    for cfg in load_configs():
        db.upsert_config(c, cfg.config_id, cfg)
    yield c
    c.close()


def add(conn, problem_id, config_id, *, think, cost, passed,
        difficulty=None, benchmark="livecodebench", finish="stop",
        error=None, is_mock=0, graded=True):
    """One synthetic (problem, config) cell with a known outcome."""
    if db.get_problem(conn, problem_id) is None:
        db.upsert_problem(conn, problem_id=problem_id, benchmark=benchmark,
                          prompt="p", entry_point="f", n_base_tests=1,
                          n_plus_tests=1, difficulty=difficulty)
    gen_id = db.insert_generation(
        conn, problem_id=problem_id, config_id=config_id,
        request_hash=f"{problem_id}:{config_id}", reasoning_tokens=think,
        completion_tokens=think + 100, cost_actual_usd=cost,
        finish_reason=finish, error=error, is_mock=is_mock)
    if graded and gen_id is not None:
        db.upsert_result(conn, gen_id,
                         GradeResult(passed, passed, 1, 1,
                                     None if passed else "assertion"))
    conn.commit()
    return gen_id


HIGH = next(c.config_id for c in load_configs() if c.effort_label == "high")
OFF = next(c.config_id for c in load_configs() if c.effort_label == "off")


# ------------------------------------------------------------ discrimination


def test_all_solved_and_none_solved_are_both_useless(conn):
    """A problem everyone solves carries as much signal as one nobody solves."""
    add(conn, "P/all", HIGH, think=100, cost=0.01, passed=True)
    add(conn, "P/all", OFF, think=0, cost=0.001, passed=True)
    add(conn, "P/none", HIGH, think=100, cost=0.01, passed=False)
    add(conn, "P/none", OFF, think=0, cost=0.001, passed=False)
    add(conn, "P/split", HIGH, think=100, cost=0.01, passed=True)
    add(conn, "P/split", OFF, think=0, cost=0.001, passed=False)

    b = analysis.discriminating_problems(conn)
    assert b["all solved"] == 1
    assert b["none solved"] == 1
    assert b["discriminating"] == 1


# ------------------------------------------------------------------- costing


def test_actual_cost_is_used_not_the_price_table(conn):
    """The price table was wrong by 1.54x once. Only the bill is trusted."""
    db.upsert_problem(conn, problem_id="P/1", benchmark="livecodebench",
                      prompt="p", entry_point="f", n_base_tests=1, n_plus_tests=1)
    gen_id = db.insert_generation(
        conn, problem_id="P/1", config_id=HIGH, request_hash="h",
        reasoning_tokens=500, cost_computed_usd=0.001,
        cost_actual_usd=0.009, is_mock=0)
    db.upsert_result(conn, gen_id, GradeResult(True, True, 1, 1, None))
    conn.commit()
    total = sum(r["total_usd"] for r in analysis.waste(conn))
    assert total == pytest.approx(0.009), "computed cost was used instead of actual"


def test_mock_rows_are_excluded_everywhere(conn):
    add(conn, "P/real", HIGH, think=100, cost=0.01, passed=True)
    add(conn, "P/fake", HIGH, think=9999, cost=99.0, passed=False, is_mock=1)
    assert sum(r["total_usd"] for r in analysis.waste(conn)) == pytest.approx(0.01)
    assert all(r["max_reasoning"] < 9999 for r in analysis.reasoning_by_tier(conn))


# --------------------------------------------------------------------- waste


def test_truncated_and_errored_calls_count_as_wasted(conn):
    """Both produce a bill and no answer, which is the category that matters."""
    add(conn, "P/trunc", HIGH, think=9000, cost=0.02, passed=False,
        finish="length")
    add(conn, "P/err", HIGH, think=800, cost=0.01, passed=False,
        error="provider finish_reason=error", graded=False)
    add(conn, "P/ok", HIGH, think=500, cost=0.005, passed=True)

    by = {r["outcome"]: r for r in analysis.waste(conn)}
    assert by["wasted (no answer)"]["n"] == 2
    assert by["wasted (no answer)"]["total_usd"] == pytest.approx(0.03)
    assert by["passed"]["n"] == 1


def test_a_truncated_call_is_never_counted_as_a_pass(conn):
    """finish_reason='length' means no answer, whatever `passed` happens to say."""
    add(conn, "P/x", HIGH, think=9000, cost=0.02, passed=True, finish="length")
    curve = analysis.abort_curve(conn, thresholds=(16000,))
    assert curve[0].passes_total == 0


# --------------------------------------------------------------- abort curve


def test_aborted_calls_cost_nothing(conn):
    """Measured, not assumed: cancelling a stream is billed $0.00."""
    add(conn, "P/cheap", HIGH, think=1000, cost=0.01, passed=True)
    add(conn, "P/dear", HIGH, think=9000, cost=0.09, passed=False,
        finish="length")

    pt = next(p for p in analysis.abort_curve(conn, thresholds=(5000,))
              if p.threshold == 5000)
    assert pt.cost_usd == pytest.approx(0.01), "the aborted call still cost money"
    assert pt.aborted == 1
    assert pt.saved_pct == pytest.approx(90.0)


def test_threshold_above_everything_changes_nothing(conn):
    add(conn, "P/a", HIGH, think=1000, cost=0.01, passed=True)
    add(conn, "P/b", HIGH, think=2000, cost=0.02, passed=True)
    pt = analysis.abort_curve(conn, thresholds=(99999,))[0]
    assert pt.aborted == 0
    assert pt.saved_pct == pytest.approx(0.0)
    assert pt.passes_kept == pt.passes_total == 2


def test_best_threshold_saves_money_and_loses_nothing(conn):
    """The headline number: it must be free, not a tradeoff."""
    for i in range(3):                      # cheap successes
        add(conn, f"P/ok{i}", HIGH, think=1000, cost=0.01, passed=True)
    for i in range(2):                      # expensive non-answers
        add(conn, f"P/bad{i}", HIGH, think=12000, cost=0.10, passed=False,
            finish="length")

    best = analysis.best_threshold(conn)
    assert best is not None
    assert best.passes_lost == 0, "the headline threshold must lose no solutions"
    assert best.saved_pct > 0
    assert best.threshold < 12000


def test_no_free_threshold_when_long_reasoning_succeeds(conn):
    """If long thinking pays off, there is no free saving -- and we must say so.

    This is the regression the whole finding is exposed to: the 10k threshold
    held only because nothing above it succeeded in a small sample.
    """
    add(conn, "P/short", HIGH, think=1000, cost=0.01, passed=True)
    add(conn, "P/long", HIGH, think=14000, cost=0.10, passed=True)
    assert analysis.best_threshold(conn) is None


def test_off_configs_are_excluded_from_the_curve(conn):
    """The abort only applies to calls that reason at all."""
    add(conn, "P/a", OFF, think=0, cost=0.001, passed=True)
    add(conn, "P/a", HIGH, think=5000, cost=0.05, passed=True)
    pt = analysis.abort_curve(conn, thresholds=(99999,))[0]
    assert pt.cost_usd == pytest.approx(0.05)


def test_empty_database_does_not_crash(conn):
    assert analysis.abort_curve(conn) == []
    assert analysis.best_threshold(conn) is None
    assert analysis.saturation(conn) == []


# ------------------------------------------- infrastructure vs model outcomes


def test_unbilled_errors_are_not_scored_as_model_failures(conn):
    """A 404 or 429 says nothing about the model, and must not lower its rate.

    With allow_fallbacks off, an overloaded pinned provider returns 429 and a
    row is written with error set and no charge. Counting that as a failure
    would understate the pass rate with pure infrastructure noise.
    """
    add(conn, "P/ok", HIGH, think=1000, cost=0.01, passed=True,
        difficulty="hard")
    add(conn, "P/429", HIGH, think=0, cost=0.0, passed=False,
        difficulty="hard", error="RateLimitError: 429", graded=False)

    tiers = {(r["tier"], r["effort"]): r for r in analysis.saturation(conn)}
    row = tiers[("hard", "high")]
    assert row["n"] == 1, "the unbilled 429 was counted in the denominator"
    assert row["pct"] == 100.0


def test_billed_non_answers_ARE_model_failures(conn):
    """Burning 16k tokens and returning nothing is a model outcome, not noise.

    It is also the most expensive outcome there is, so it must stay in the
    waste table -- that is the finding.
    """
    add(conn, "P/burn", HIGH, think=16000, cost=0.02, passed=False,
        finish="length", error="empty response", graded=False)
    by = {r["outcome"]: r for r in analysis.waste(conn)}
    assert by["wasted (no answer)"]["n"] == 1
    assert by["wasted (no answer)"]["total_usd"] == pytest.approx(0.02)


def test_unbilled_errors_are_excluded_from_the_abort_curve(conn):
    """They cost nothing, so aborting them saves nothing -- and they are not
    evidence either way about the threshold."""
    add(conn, "P/ok", HIGH, think=1000, cost=0.01, passed=True)
    add(conn, "P/404", HIGH, think=0, cost=0.0, passed=False,
        error="NotFoundError: no endpoints", graded=False)
    pt = analysis.abort_curve(conn, thresholds=(99999,))[0]
    assert pt.baseline_usd == pytest.approx(0.01)
    assert pt.passes_total == 1


def test_a_thinking_call_with_no_reasoning_tokens_is_still_counted(conn):
    """It is a real, billed data point and must not vanish from the curve.

    abort_curve used to filter reasoning_tokens > 0, which silently dropped
    these -- zero rows today, but it would have under-reported the baseline
    the moment one appeared.
    """
    add(conn, "P/zero", HIGH, think=0, cost=0.004, passed=True)
    pt = analysis.abort_curve(conn, thresholds=(99999,))[0]
    assert pt.baseline_usd == pytest.approx(0.004)
    assert pt.passes_total == 1


def test_censoring_is_reported_not_hidden(conn):
    """A call stopped at max_tokens has an unknown true reasoning length.

    It cannot have succeeded, so it drags the abort curve against long
    reasoning. That has to be visible next to the result, not discovered by a
    reader later.
    """
    add(conn, "P/ok", HIGH, think=1000, cost=0.01, passed=True, difficulty="hard")
    add(conn, "P/cut", HIGH, think=16000, cost=0.05, passed=False,
        difficulty="hard", finish="length", error="empty response", graded=False)

    rows = {r["tier"]: r for r in analysis.censoring(conn)}
    assert rows["hard"]["censored"] == 1
    assert rows["hard"]["pct"] == 50.0


def test_no_censoring_reported_when_nothing_was_cut_off(conn):
    add(conn, "P/ok", HIGH, think=1000, cost=0.01, passed=True)
    assert analysis.censoring(conn) == []


# --------------------------------------------- comparability and economics


def test_paired_set_requires_both_effort_arms(conn):
    """A problem with only no-reasoning results cannot inform the comparison."""
    add(conn, "P/both", HIGH, think=500, cost=0.01, passed=True)
    add(conn, "P/both", OFF, think=0, cost=0.001, passed=False)
    add(conn, "P/offonly", OFF, think=0, cost=0.001, passed=True)
    assert analysis.paired_problems(conn) == ["P/both"]


def test_unbilled_failures_do_not_make_a_problem_paired(conn):
    """A 429 means nothing ran, so there is nothing to compare against."""
    add(conn, "P/x", OFF, think=0, cost=0.001, passed=True)
    add(conn, "P/x", HIGH, think=0, cost=0.0, passed=False,
        error="RateLimitError: 429", graded=True)
    assert analysis.paired_problems(conn) == []


def test_cpc_is_total_cost_over_total_solved(conn):
    """The headline economic metric, computed the way section 13 defines it."""
    add(conn, "P/1", HIGH, think=100, cost=0.010, passed=True)
    add(conn, "P/2", HIGH, think=100, cost=0.020, passed=True)
    add(conn, "P/3", HIGH, think=100, cost=0.030, passed=False)

    row = next(r for r in analysis.cost_per_correct(
        conn, ["P/1", "P/2", "P/3"], seed=1, n_resamples=200)
        if r["config_id"] == HIGH)
    assert row["solved"] == 2
    assert row["total_usd"] == pytest.approx(0.06)
    assert row["cpc_usd"] == pytest.approx(0.03), "CPC must be 0.06/2, not a mean"


def test_cpc_is_none_when_a_config_solved_nothing(conn):
    """Real on the hard tier. Must not divide by zero."""
    add(conn, "P/1", HIGH, think=100, cost=0.01, passed=False)
    row = next(r for r in analysis.cost_per_correct(conn, ["P/1"], seed=1,
                                                    n_resamples=50)
               if r["config_id"] == HIGH)
    assert row["cpc_usd"] is None
    assert row["solved"] == 0


def test_cpc_interval_brackets_the_point_estimate(conn):
    for i in range(30):
        add(conn, f"P/{i}", HIGH, think=100, cost=0.01, passed=(i % 2 == 0))
    row = next(r for r in analysis.cost_per_correct(
        conn, [f"P/{i}" for i in range(30)], seed=5, n_resamples=400)
        if r["config_id"] == HIGH)
    assert row["cpc_lo"] <= row["cpc_usd"] <= row["cpc_hi"]


def test_abort_curve_ci_resamples_problems_not_cells(conn):
    """Cells on one problem are not independent observations of difficulty.

    Resampling cells would understate every interval, which is the failure mode
    that makes a bootstrap worse than useless.
    """
    for i in range(20):
        # two thinking cells per problem, deliberately correlated
        add(conn, f"P/{i}", HIGH, think=1000, cost=0.01, passed=True)
    curve = analysis.abort_curve_ci(conn, thresholds=(5000,), seed=1,
                                    n_resamples=300)
    assert curve[0]["n_problems"] == 20, "resampling unit is not the problem"


def test_abort_curve_ci_intervals_are_ordered(conn):
    for i in range(25):
        add(conn, f"P/{i}", HIGH, think=1000 * (i + 1), cost=0.01,
            passed=(i < 12))
    for c in analysis.abort_curve_ci(conn, seed=2, n_resamples=300):
        if not (c["kept_lo"] != c["kept_lo"]):        # skip NaN
            assert c["kept_lo"] <= c["kept_hi"]
            assert c["saved_lo"] <= c["saved_hi"]


# ------------------------------------------------- frontier geometry (RQ4)


def test_pareto_drops_dominated_points():
    """A point beaten on BOTH axes is never worth choosing."""
    pts = [
        {"config_id": 1, "cost": 1.0, "accuracy": 50.0},
        {"config_id": 2, "cost": 2.0, "accuracy": 90.0},
        {"config_id": 3, "cost": 3.0, "accuracy": 60.0},   # dominated by 2
    ]
    kept = {p["config_id"] for p in analysis.pareto_front(pts)}
    assert kept == {1, 2}


def test_hull_drops_points_a_mixture_beats():
    """The middle point here is below the line from 1 to 3, so mixing beats it.

    This is section 10.1's whole argument: a config can be Pareto-optimal and
    still be worthless, because randomising between its neighbours dominates it.
    """
    pts = [
        {"config_id": 1, "cost": 0.0, "accuracy": 0.0},
        {"config_id": 2, "cost": 1.0, "accuracy": 40.0},   # under the chord
        {"config_id": 3, "cost": 2.0, "accuracy": 100.0},
    ]
    assert {p["config_id"] for p in analysis.pareto_front(pts)} == {1, 2, 3}
    assert {p["config_id"] for p in analysis.upper_hull(pts)} == {1, 3}


def test_hull_keeps_a_point_above_the_chord(conn):
    pts = [
        {"config_id": 1, "cost": 0.0, "accuracy": 0.0},
        {"config_id": 2, "cost": 1.0, "accuracy": 80.0},   # above the chord
        {"config_id": 3, "cost": 2.0, "accuracy": 100.0},
    ]
    assert {p["config_id"] for p in analysis.upper_hull(pts)} == {1, 2, 3}


def test_hull_accuracy_interpolates_between_vertices():
    """Section 10.1: the optimum mixes at most TWO configs, so it is linear."""
    hull = [{"cost": 0.0, "accuracy": 0.0}, {"cost": 2.0, "accuracy": 100.0}]
    assert analysis.hull_accuracy_at(hull, 1.0) == pytest.approx(50.0)
    assert analysis.hull_accuracy_at(hull, 2.0) == pytest.approx(100.0)
    assert analysis.hull_accuracy_at(hull, 5.0) == pytest.approx(100.0)
    assert analysis.hull_accuracy_at(hull, -1.0) is None, "nothing is affordable"


def test_oracle_picks_the_cheapest_config_that_solved_each_problem(conn):
    """The MCKP integer optimum, not an ad-hoc ceiling."""
    add(conn, "P/1", OFF, think=0, cost=0.001, passed=False)
    add(conn, "P/1", HIGH, think=500, cost=0.010, passed=True)   # only winner
    add(conn, "P/2", OFF, think=0, cost=0.002, passed=True)      # cheap winner
    add(conn, "P/2", HIGH, think=500, cost=0.020, passed=True)

    o = analysis.oracle(conn, [OFF, HIGH], ["P/1", "P/2"])
    assert o["solved"] == 2
    assert o["accuracy"] == pytest.approx(100.0)
    # 0.010 (only option for P/1) + 0.002 (cheapest winner for P/2), over 2
    assert o["cost"] == pytest.approx((0.010 + 0.002) / 2)


def test_oracle_still_pays_for_problems_nobody_solved(conn):
    """Pretending an unsolved problem is free would flatter the oracle."""
    add(conn, "P/x", OFF, think=0, cost=0.003, passed=False)
    add(conn, "P/x", HIGH, think=500, cost=0.030, passed=False)
    o = analysis.oracle(conn, [OFF, HIGH], ["P/x"])
    assert o["solved"] == 0
    assert o["cost"] == pytest.approx(0.003), "should pay the cheapest attempt"


def test_common_problems_requires_every_named_config(conn):
    add(conn, "P/both", OFF, think=0, cost=0.001, passed=True)
    add(conn, "P/both", HIGH, think=500, cost=0.01, passed=True)
    add(conn, "P/one", OFF, think=0, cost=0.001, passed=True)
    assert analysis.common_problems(conn, [OFF, HIGH]) == ["P/both"]
