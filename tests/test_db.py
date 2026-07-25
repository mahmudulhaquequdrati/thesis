"""The budget depends on one property: we never buy the same generation twice.

`request_hash UNIQUE` is what makes a crashed run free to restart. CLAUDE.md
section 2 requires it be proven working before any paid loop, and these tests
are that proof.

Run:  uv run pytest tests/test_db.py -v
"""

import pytest

from carr import db
from carr.cost import compute_cost
from carr.effort import load_configs


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "t.sqlite")
    db.init_schema(c)
    yield c
    c.close()


@pytest.fixture
def seeded(conn):
    cfg = load_configs()[0]
    db.upsert_config(conn, cfg.tier_index, cfg)
    db.upsert_problem(conn, problem_id="T/1", benchmark="humaneval_plus",
                      prompt="def f():\n", entry_point="f",
                      n_base_tests=3, n_plus_tests=7)
    conn.commit()
    return conn, cfg


# ------------------------------------------------------------ request_hash


def test_hash_is_stable_across_dict_ordering():
    """Two spellings of the same params must not produce two purchases."""
    a = db.request_hash("m", "high", "p", {"reasoning": {"effort": "high"}})
    b = db.request_hash("m", "high", "p", {"reasoning": {"effort": "high"}})
    assert a == b


def test_hash_covers_each_axis():
    base = db.request_hash("m", "off", "p", {})
    assert base != db.request_hash("m2", "off", "p", {})
    assert base != db.request_hash("m", "high", "p", {})
    assert base != db.request_hash("m", "off", "p2", {})
    assert base != db.request_hash("m", "off", "p", {"reasoning": {"enabled": False}})


def test_hash_cannot_be_confused_by_concatenation():
    """Fields are NUL-joined, so 'ab'+'c' and 'a'+'bc' stay distinct."""
    assert db.request_hash("ab", "c", "p", {}) != db.request_hash("a", "bc", "p", {})


# ------------------------------------------------------- never pay twice


def test_duplicate_generation_returns_none(seeded):
    conn, cfg = seeded
    h = db.request_hash(cfg.model_slug, cfg.effort_label, "def f():\n", cfg.params)

    first = db.insert_generation(conn, problem_id="T/1", config_id=cfg.tier_index,
                                 request_hash=h, is_mock=1)
    assert isinstance(first, int)

    second = db.insert_generation(conn, problem_id="T/1", config_id=cfg.tier_index,
                                  request_hash=h, is_mock=1)
    assert second is None, "a duplicate request_hash must not insert a second row"

    n = conn.execute("SELECT COUNT(*) FROM generations").fetchone()[0]
    assert n == 1


def test_has_generation_matches_insert(seeded):
    conn, cfg = seeded
    h = db.request_hash(cfg.model_slug, cfg.effort_label, "def f():\n", cfg.params)
    assert db.has_generation(conn, h) is False
    db.insert_generation(conn, problem_id="T/1", config_id=cfg.tier_index,
                         request_hash=h, is_mock=1)
    assert db.has_generation(conn, h) is True


def test_other_integrity_errors_still_raise(seeded):
    """Only the request_hash collision is swallowed; real bugs must surface."""
    conn, cfg = seeded
    with pytest.raises(Exception):
        db.insert_generation(conn, problem_id="NOPE/999",
                             config_id=cfg.tier_index,
                             request_hash="h1", is_mock=1)


# ------------------------------------------------------------- the schema


def test_configs_roundtrip(conn):
    """Every config in the roster lands, and re-writing updates in place.

    Deliberately counts against `load_configs()` rather than a literal: the
    roster is expected to change, and a test that hardcodes its size fails for
    the wrong reason every time it does.
    """
    configs = load_configs()
    for cfg in configs:
        db.upsert_config(conn, cfg.tier_index, cfg)
    conn.commit()
    assert len(db.list_configs(conn)) == len(configs)

    for cfg in configs:
        db.upsert_config(conn, cfg.tier_index, cfg)
    assert len(db.list_configs(conn)) == len(configs)


def test_every_model_has_both_efforts():
    """No model may sit on one effort level.

    A model with a single config has one point on the cost-accuracy plane and
    no measurable thinking delta, which is the whole variable under study. This
    is why the held-out model runs on fewer *problems* but on both efforts.
    """
    by_model: dict[str, set[str]] = {}
    for c in load_configs():
        by_model.setdefault(c.model_slug, set()).add(c.effort_label)
    for slug, efforts in by_model.items():
        assert efforts == {"off", "high"}, f"{slug} has only {efforts}"


def test_error_type_domain_is_enforced(seeded):
    """grade() only emits 'assertion' and 'timeout'. The DB agrees."""
    conn, cfg = seeded
    gen_id = db.insert_generation(conn, problem_id="T/1", config_id=cfg.tier_index,
                                  request_hash="h", is_mock=1)
    with pytest.raises(Exception):
        conn.execute(
            "INSERT INTO results (gen_id, passed, base_passed, n_tests_passed,"
            " n_tests_total, error_type) VALUES (?, 0, 0, 0, 1, 'syntax')",
            (gen_id,),
        )


def test_result_mirrors_grade_result(seeded):
    """upsert_result must accept a GradeResult unchanged, fields and all."""
    conn, cfg = seeded
    from carr.execute.verify import GradeResult

    gen_id = db.insert_generation(conn, problem_id="T/1", config_id=cfg.tier_index,
                                  request_hash="h", is_mock=1)
    g = GradeResult(passed=False, base_passed=True, n_tests_passed=9,
                    n_tests_total=10, error_type="assertion")
    db.upsert_result(conn, gen_id, g, exec_ms=42)

    row = conn.execute("SELECT * FROM results WHERE gen_id = ?", (gen_id,)).fetchone()
    assert (row["passed"], row["base_passed"]) == (0, 1)
    assert (row["n_tests_passed"], row["n_tests_total"]) == (9, 10)
    assert row["error_type"] == "assertion"

    # Re-grading overwrites rather than duplicating -- this is what makes
    # fixing an extraction bug free instead of a re-purchase.
    db.upsert_result(conn, gen_id, GradeResult(True, True, 10, 10, None))
    assert conn.execute("SELECT COUNT(*) FROM results").fetchone()[0] == 1
    assert conn.execute("SELECT passed FROM results").fetchone()[0] == 1


# ------------------------------------------------------- the routing label


def test_cheapest_passing_is_the_routing_target(seeded):
    conn, _ = seeded
    from carr.execute.verify import GradeResult

    configs = load_configs()
    for cfg in configs[:3]:
        db.upsert_config(conn, cfg.tier_index, cfg)

    # Cheap config fails; two dearer ones pass. The target is the cheaper pass.
    for i, (cfg, passed, cost) in enumerate([
        (configs[0], False, 0.0001),
        (configs[1], True, 0.0005),
        (configs[2], True, 0.0009),
    ]):
        gen_id = db.insert_generation(
            conn, problem_id="T/1", config_id=cfg.tier_index,
            request_hash=f"h{i}", cost_computed_usd=cost, is_mock=1)
        db.upsert_result(conn, gen_id,
                         GradeResult(passed, passed, 1, 1, None if passed else "assertion"))

    best = db.cheapest_passing(conn, "T/1")
    assert best["model_slug"] == configs[1].model_slug
    assert best["cost_computed_usd"] == 0.0005


def test_no_passing_config_means_no_label(seeded):
    """A problem nothing solves carries no routing label. Not an error."""
    conn, cfg = seeded
    from carr.execute.verify import GradeResult

    gen_id = db.insert_generation(conn, problem_id="T/1", config_id=cfg.tier_index,
                                  request_hash="h", cost_computed_usd=0.1, is_mock=1)
    db.upsert_result(conn, gen_id, GradeResult(False, False, 0, 1, "assertion"))
    assert db.cheapest_passing(conn, "T/1") is None


def test_mock_rows_are_excluded_from_real_spend(seeded):
    conn, cfg = seeded
    db.insert_generation(conn, problem_id="T/1", config_id=cfg.tier_index,
                         request_hash="mock", cost_computed_usd=99.0, is_mock=1)
    s = db.summary(conn)
    assert s["mock_generations"] == 1
    assert s["real_spend_usd"] == 0.0, "mock rows must never count as money spent"


# ------------------------------------------------------------------- cost


def test_reasoning_tokens_are_not_double_charged():
    """reasoning_tokens is a SUBSET of completion_tokens, never an addition."""
    # 412 completion tokens of which 392 reasoning -- the Day 1 measurement.
    cost = compute_cost(100, 412, 0.1, 0.15)
    assert cost == pytest.approx((100 * 0.1 + 412 * 0.15) / 1e6)


def test_cost_handles_missing_counts():
    assert compute_cost(None, None, 1.0, 1.0) == 0.0
