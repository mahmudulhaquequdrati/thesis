"""The cost cap must abort, and it must abort before spending.

This is the code that stands between a bug and an empty OpenRouter account.
CLAUDE.md section 2: "Never run a paid loop without a cost cap that aborts.
Warn-and-continue is not a cap." These tests are what makes that claim true
rather than aspirational.

The provider here is a local stub -- no network, no key, no cost. It exists
only to make the runner's arithmetic observable.

Run:  uv run pytest tests/test_runner.py -v
"""

import pytest

from carr import db, runner
from carr.effort import load_configs
from carr.experiment import load_experiment, sample_problems
from carr.providers.base import Generation, Usage

TRIVIAL_CODE = "```python\ndef f():\n    return 1\n```"


class StubProvider:
    """Returns a fixed number of tokens per call. Never touches the network."""

    name = "stub"

    def __init__(self, completion_tokens=1000, reasoning_tokens=0, fail=False):
        self.completion_tokens = completion_tokens
        self.reasoning_tokens = reasoning_tokens
        self.fail = fail
        self.calls = []

    def complete(self, prompt, config, *, problem_id, max_tokens=16000,
                 temperature=0.0):
        self.calls.append((problem_id, config.label))
        if self.fail:
            return Generation(error="stub failure", latency_ms=1)
        return Generation(
            raw_response=TRIVIAL_CODE,
            usage=Usage(prompt_tokens=100,
                        completion_tokens=self.completion_tokens,
                        reasoning_tokens=self.reasoning_tokens),
            finish_reason="stop", latency_ms=1,
            provider_gen_id=f"stub-{len(self.calls)}",
        )


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "t.sqlite")
    db.init_schema(c)
    for cfg in load_configs():
        db.upsert_config(c, cfg.config_id, cfg)
    for i in range(4):
        db.upsert_problem(c, problem_id=f"T/{i}", benchmark="humaneval_plus",
                          prompt=f"def f{i}():\n    pass\n", entry_point="f",
                          n_base_tests=1, n_plus_tests=1)
    c.commit()
    yield c
    c.close()


# ------------------------------------------------------------------ planning


def test_plan_covers_every_cell(conn):
    configs = load_configs()
    cells, skipped = runner.plan(conn, ["T/0", "T/1"], configs)
    assert len(cells) == 2 * len(configs)
    assert skipped == 0


def test_plan_is_cheapest_first_globally(conn):
    """Every cheap cell before any expensive one, ACROSS problems.

    Per-problem ordering would leave a cap abort with a random half of each
    problem. Global ordering leaves a complete cheap foundation instead.
    """
    cells, _ = runner.plan(conn, ["T/0", "T/1", "T/2"], load_configs())
    costs = [c.expected_usd() for c in cells]
    assert costs == sorted(costs)
    # The first cells must all be reasoning-off ones.
    assert cells[0].config.effort_label == "off"
    assert cells[-1].config.effort_label == "high"


def test_plan_skips_already_bought(conn):
    configs = load_configs()[:2]
    cells, _ = runner.plan(conn, ["T/0"], configs)
    runner.run(conn, cells[:1], StubProvider(), max_tokens=16000,
               abort_at_usd=10.0)
    cells2, skipped = runner.plan(conn, ["T/0"], configs)
    assert skipped == 1
    assert len(cells2) == len(configs) - 1


# ---------------------------------------------------------------- the cap


def test_cap_stops_before_spending(conn):
    """A zero-headroom cap must buy NOTHING, not one call's worth."""
    cells, _ = runner.plan(conn, ["T/0"], load_configs())
    provider = StubProvider()
    report = runner.run(conn, cells, provider, max_tokens=16000, abort_at_usd=0.0)

    assert provider.calls == [], "the cap let a call through"
    assert report.bought == 0
    assert report.spent_usd == 0.0
    assert report.stopped_reason is not None
    assert conn.execute("SELECT COUNT(*) FROM generations").fetchone()[0] == 0


def test_cap_uses_worst_case_not_expected(conn):
    """A cap set above the expected cost but below the worst case must refuse.

    This is the whole design: an expected-case cap is not a cap, because the
    situation it exists for is precisely the one where the estimate is wrong.
    """
    cells, _ = runner.plan(conn, ["T/0"], load_configs()[:1])
    cell = cells[0]
    expected, worst = cell.expected_usd(), cell.worst_usd(16000)
    assert expected < worst

    between = (expected + worst) / 2
    provider = StubProvider()
    report = runner.run(conn, cells, provider, max_tokens=16000,
                        abort_at_usd=between)
    assert provider.calls == []
    assert report.bought == 0


def test_cap_counts_lifetime_spend_not_just_this_run(conn):
    """Five runs each under their own limit still empty the account."""
    cells, _ = runner.plan(conn, ["T/0"], load_configs()[:1])
    runner.run(conn, cells, StubProvider(), max_tokens=16000, abort_at_usd=10.0)
    spent = runner.lifetime_spend(conn)
    assert spent > 0

    # A second run whose cap is below what has ALREADY been spent buys nothing.
    cells2, _ = runner.plan(conn, ["T/1"], load_configs()[:1])
    provider = StubProvider()
    report = runner.run(conn, cells2, provider, max_tokens=16000,
                        abort_at_usd=spent * 0.5)
    assert provider.calls == []
    assert report.bought == 0


def test_run_stops_partway_and_is_resumable(conn):
    """A cap that fires mid-run leaves the cheap cells bought and the rest free."""
    configs = load_configs()
    cells, _ = runner.plan(conn, ["T/0", "T/1"], configs)
    # Enough headroom for a few of the cheapest cells, not for all of them.
    cap = sum(c.worst_usd(16000) for c in cells[:3]) * 0.9

    report = runner.run(conn, cells, StubProvider(), max_tokens=16000,
                        abort_at_usd=cap)
    assert 0 < report.bought < len(cells)
    assert report.stopped_reason is not None

    # Resuming re-plans and skips exactly what was bought.
    cells2, skipped = runner.plan(conn, ["T/0", "T/1"], configs)
    assert skipped == report.bought
    assert len(cells2) == len(cells) - report.bought


# ------------------------------------------------------------------ storage


def test_rows_are_marked_real_not_mock(conn):
    cells, _ = runner.plan(conn, ["T/0"], load_configs()[:1])
    runner.run(conn, cells, StubProvider(), max_tokens=16000, abort_at_usd=10.0)
    row = conn.execute("SELECT is_mock, temperature_sent, openrouter_gen_id "
                       "FROM generations").fetchone()
    assert row["is_mock"] == 0
    assert row["temperature_sent"] == 0.0
    assert row["openrouter_gen_id"] is not None


def test_failed_call_is_recorded_without_a_result(conn):
    """An API error is a row, not an exception. A grid must survive a 502."""
    cells, _ = runner.plan(conn, ["T/0"], load_configs()[:1])
    report = runner.run(conn, cells, StubProvider(fail=True), max_tokens=16000,
                        abort_at_usd=10.0)
    assert report.bought == 1
    assert report.errors == 1
    assert report.graded == 0
    assert conn.execute("SELECT COUNT(*) FROM results").fetchone()[0] == 0
    assert conn.execute("SELECT error FROM generations").fetchone()[0] is not None


def test_reasoning_tokens_are_stored_and_not_double_charged(conn):
    cells, _ = runner.plan(conn, ["T/0"], load_configs()[:1])
    provider = StubProvider(completion_tokens=4000, reasoning_tokens=3500)
    runner.run(conn, cells, provider, max_tokens=16000, abort_at_usd=10.0)

    row = conn.execute("SELECT completion_tokens, reasoning_tokens, "
                       "cost_computed_usd FROM generations").fetchone()
    assert row["completion_tokens"] == 4000
    assert row["reasoning_tokens"] == 3500
    cfg = load_configs()[0]
    expected = (100 * cfg.price_in_per_m + 4000 * cfg.price_out_per_m) / 1e6
    assert row["cost_computed_usd"] == pytest.approx(expected)


# ----------------------------------------------------------------- sampling


def test_sample_is_deterministic(conn):
    strata = {"humaneval_plus": 2}
    a = sample_problems(conn, strata, seed=1)
    b = sample_problems(conn, strata, seed=1)
    assert a == b
    assert len(a) == 2


def test_sample_is_seed_sensitive(conn):
    for i in range(20):
        db.upsert_problem(conn, problem_id=f"H/{i}", benchmark="humaneval_plus",
                          prompt="x", entry_point="f",
                          n_base_tests=1, n_plus_tests=1)
    conn.commit()
    strata = {"humaneval_plus": 5}
    assert sample_problems(conn, strata, seed=1) != sample_problems(conn, strata, seed=2)


def test_sample_does_not_depend_on_other_strata(conn):
    """Adding a stratum must not change which problems the others pick.

    Otherwise growing the pilot silently reshuffles the sample and the two runs
    are not comparable.
    """
    for i in range(20):
        db.upsert_problem(conn, problem_id=f"H/{i}", benchmark="humaneval_plus",
                          prompt="x", entry_point="f",
                          n_base_tests=1, n_plus_tests=1)
        db.upsert_problem(conn, problem_id=f"M/{i}", benchmark="mbpp_plus",
                          prompt="x", entry_point="f",
                          n_base_tests=1, n_plus_tests=1)
    conn.commit()
    alone = sample_problems(conn, {"humaneval_plus": 4}, seed=7)
    together = sample_problems(conn, {"humaneval_plus": 4, "mbpp_plus": 4}, seed=7)
    assert alone == [p for p in together if p.startswith(("H/", "T/"))]


def test_empty_stratum_is_an_error_not_a_silent_skip(conn):
    with pytest.raises(ValueError, match="empty"):
        sample_problems(conn, {"livecodebench_hard": 3}, seed=1)


def test_experiment_config_loads_and_is_sane():
    exp = load_experiment()
    assert exp.budget.abort_at_usd <= exp.budget.loaded_usd, \
        "the abort cap must sit below the money actually on the account"
    assert exp.budget.loaded_usd <= exp.budget.max_spend_usd
    assert exp.generation.temperature == 0.0
    assert exp.generation.retries == 0, "a retry loop defeats the cost cap"
    assert sum(exp.pilot_strata.values()) > 0
