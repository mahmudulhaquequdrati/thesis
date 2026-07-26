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
