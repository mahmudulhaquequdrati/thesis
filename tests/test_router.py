"""The router and its gap decomposition.

The decomposition is the part THESIS.md section 10.2 calls "the most genuinely
yours", and it is the thing that turns a negative result into a diagnostic one.
If it mis-attributes a shortfall to features when the estimator is at fault, it
would send the whole write-up in the wrong direction.

Run:  uv run pytest tests/test_router.py -v
"""

import pytest

from carr import db, router
from carr.effort import load_configs
from carr.execute.verify import GradeResult

CHEAP = next(c.config_id for c in load_configs() if c.effort_label == "off")
DEAR = next(c.config_id for c in load_configs() if c.effort_label == "high")


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "r.sqlite")
    db.init_schema(c)
    for cfg in load_configs():
        db.upsert_config(c, cfg.config_id, cfg)
    yield c
    c.close()


def cell(conn, pid, cid, *, solved, cost, tier="hard", n_tests=40, chars=1000):
    bench = "livecodebench" if tier in ("easy", "medium", "hard") else tier
    if db.get_problem(conn, pid) is None:
        db.upsert_problem(conn, problem_id=pid, benchmark=bench,
                          prompt="x" * chars, entry_point="f",
                          n_base_tests=n_tests, n_plus_tests=0,
                          difficulty=tier if bench == "livecodebench" else None)
    gid = db.insert_generation(conn, problem_id=pid, config_id=cid,
                               request_hash=f"{pid}:{cid}",
                               cost_actual_usd=cost, completion_tokens=100,
                               reasoning_tokens=0, is_mock=0)
    db.upsert_result(conn, gid, GradeResult(solved, solved, 1, 1,
                                            None if solved else "assertion"))
    conn.commit()


# ------------------------------------------------------------------ features


def test_features_are_free():
    """No forward pass, no drafts -- that is the whole 'cheapest router' claim.

    Every field must be readable from the problem statement before any token is
    bought.
    """
    p = router.Problem("P/1", "hard", 40, 1000)
    feats = p.features()
    assert len(feats) == 3
    assert all(0.0 <= f <= 1.0 for f in feats), "features must be scaled"


def test_difficulty_is_ordinal_and_ordered():
    ranks = [router.Problem("p", t, 1, 1).rank
             for t in ("mbpp_plus", "humaneval_plus", "easy", "medium", "hard")]
    assert ranks == sorted(ranks), "tiers must be ordered easy to hard"


# ------------------------------------------------------------- the label


def test_label_is_the_cheapest_config_that_actually_solved(conn):
    got = router.cheapest_solving({
        1: {"solved": 1, "cost": 0.05},
        2: {"solved": 1, "cost": 0.01},     # cheaper AND solves -> the label
        3: {"solved": 0, "cost": 0.001},    # cheapest but fails
    })
    assert got == 2


def test_no_label_when_nothing_solved(conn):
    """A problem nothing solves teaches a router nothing and must be skipped."""
    assert router.cheapest_solving({1: {"solved": 0, "cost": 0.01}}) is None


# ------------------------------------------------------------ evaluation


def test_evaluation_never_trains_on_the_held_out_problem(conn):
    """Leave-one-out must actually leave one out, or every score is inflated."""
    seen = []

    def spy(problem, train, grid):
        seen.append((problem.problem_id,
                     {p.problem_id for p in train}))
        return CHEAP

    for i in range(5):
        cell(conn, f"P/{i}", CHEAP, solved=True, cost=0.001)
    router.evaluate(conn, spy, [CHEAP], [f"P/{i}" for i in range(5)],
                    fallback=CHEAP)

    assert len(seen) == 5
    for pid, train in seen:
        assert pid not in train, f"{pid} was in its own training set"


def test_a_router_cannot_win_by_abstaining(conn):
    """Returning None falls back to a real config and is scored on it."""
    for i in range(4):
        cell(conn, f"P/{i}", CHEAP, solved=False, cost=0.001)
    e = router.evaluate(conn, lambda p, t, g: None, [CHEAP],
                        [f"P/{i}" for i in range(4)], fallback=CHEAP)
    assert e["n"] == 4
    assert e["accuracy"] == 0.0, "abstaining scored better than the fallback"


def test_perfect_router_matches_the_oracle(conn):
    """Sanity: a router given the answers should reach oracle accuracy."""
    for i in range(6):
        hard = i % 2 == 0
        cell(conn, f"P/{i}", CHEAP, solved=not hard, cost=0.001,
             tier="hard" if hard else "easy")
        cell(conn, f"P/{i}", DEAR, solved=True, cost=0.02,
             tier="hard" if hard else "easy")

    ids = [f"P/{i}" for i in range(6)]
    cheat = lambda p, t, g: router.cheapest_solving(g[p.problem_id])  # noqa: E731
    e = router.evaluate(conn, cheat, [CHEAP, DEAR], ids, fallback=CHEAP)
    assert e["accuracy"] == 100.0


# ------------------------------------------------------- gap decomposition


def test_decomposition_blames_the_estimator_when_features_suffice(conn):
    """The distinction the whole section exists to make.

    Difficulty perfectly determines which config works here, so the features
    are sufficient and any shortfall is the estimator's fault. Feature
    insufficiency must come out at ~0.
    """
    for i in range(20):
        hard = i % 2 == 0
        tier = "hard" if hard else "mbpp_plus"
        cell(conn, f"P/{i}", CHEAP, solved=not hard, cost=0.001, tier=tier)
        cell(conn, f"P/{i}", DEAR, solved=True, cost=0.02, tier=tier)

    d = router.decompose_gap(conn, [CHEAP, DEAR], [f"P/{i}" for i in range(20)])
    assert d["feature_insufficiency"] == pytest.approx(0.0, abs=1e-6), \
        "features fully determine the answer, so they cannot be the shortfall"
    assert d["oracle"]["accuracy"] == pytest.approx(100.0)


def test_decomposition_blames_features_when_they_are_uninformative(conn):
    """Identical features, different answers: no router can tell them apart.

    Every problem looks the same, so the feature ceiling must fall short of the
    oracle and the shortfall must be attributed to the features.
    """
    for i in range(20):
        cell(conn, f"P/{i}", CHEAP, solved=(i % 2 == 0), cost=0.001,
             tier="hard", n_tests=40, chars=1000)
        cell(conn, f"P/{i}", DEAR, solved=(i % 2 == 1), cost=0.02,
             tier="hard", n_tests=40, chars=1000)

    d = router.decompose_gap(conn, [CHEAP, DEAR], [f"P/{i}" for i in range(20)])
    assert d["oracle"]["accuracy"] == pytest.approx(100.0)
    assert d["feature_insufficiency"] > 40, \
        "indistinguishable problems must be blamed on the features"


def test_collapse_is_visible_in_the_output(conn):
    """A router that always answers the same thing must be detectable.

    'When Routing Collapses' names this, and it is what the real data does --
    reporting a collapsed router as a working one would be the worst outcome.
    """
    for i in range(12):
        cell(conn, f"P/{i}", CHEAP, solved=True, cost=0.001)
        cell(conn, f"P/{i}", DEAR, solved=True, cost=0.02)
    e = router.evaluate(conn, router.route_knn(3), [CHEAP, DEAR],
                        [f"P/{i}" for i in range(12)], fallback=CHEAP)
    assert e["distinct_configs_used"] == 1
