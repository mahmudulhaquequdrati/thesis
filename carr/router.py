"""The router, and the decomposition of why it falls short. Free -- no API calls.

This is RQ4, demoted to one section by the reframing but still worth measuring,
plus the piece THESIS.md section 10.2 calls "the most genuinely yours":

    Oracle-gap decomposition. Split the CARR->oracle gap into feature
    insufficiency + label noise + estimation error. This is the most genuinely
    yours, and it converts a negative result into a diagnostic one.

**Every feature here is free of API cost** -- no forward pass, no draft answer,
no hidden states, no embedding model. A router that must first call a model to
decide whether to call a model has already spent the money it was trying to
save, which is the "cheapest possible router" claim in section 15.3.

⚠️ **But "free" is not the same as "available", and this file used to claim it
was. Two of the three features are BENCHMARK METADATA, not properties of an
incoming prompt:**

    rank          <- COALESCE(difficulty, benchmark). `difficulty` is
                     LiveCodeBench's OWN hardness label, assigned by the
                     benchmark; for HumanEval+/MBPP+ it degrades to the
                     benchmark name. A user arriving with a new problem does
                     not have this, and if they could label difficulty reliably
                     they would already have solved most of the routing problem.
    n_tests       <- problems.n_tests, which is base + plus, i.e. the size of
                     the HIDDEN GRADING SUITE. It is not knowable before the
                     problem has been graded. db.py's schema comment even labels
                     it "A CARR router feature".
    prompt_chars  <- the only one genuinely computable from the incoming prompt.

So the proposal's positioning -- routing "using only cheap, non-LLM structural
and lexical features" of the arriving prompt -- is NOT what this implements, and
that is true independently of whether the router worked. Report it as a
limitation of the feature set, and note the consequence for feature_ceiling()
below: "these features are sufficient to reach the oracle" is a much weaker
statement than it sounds, because two thirds of them are metadata a deployment
would not have.

A genuinely deployable version has one feature (prompt length) plus whatever
else can be computed from the prompt text -- keyword presence, code-block
structure, requested signature count -- and none of that was measured here.

The honest baseline is the convex hull, not the best single config. If you may
split traffic between two configurations, everything on the line between them is
achievable, so beating the best single config is nearly free and proves little
(section 10.1). The hull is what `carr/analysis.py` computes.

Evaluation is leave-one-out cross-validation, because the usable set is ~60
problems and a single train/test split at that size measures the split more than
the method.
"""

from __future__ import annotations

from dataclasses import dataclass

from carr import analysis

# Ordinal, because the tiers really are ordered and a router should be able to
# use that. The easy benchmarks sit below LiveCodeBench-easy: measured pass
# rates are 72-97% against 94-100%.
DIFFICULTY_RANK = {"mbpp_plus": 0, "humaneval_plus": 1,
                   "easy": 2, "medium": 3, "hard": 4}


@dataclass
class Problem:
    problem_id: str
    tier: str
    n_tests: int
    prompt_chars: int

    @property
    def rank(self) -> int:
        return DIFFICULTY_RANK.get(self.tier, 2)

    def features(self) -> tuple[float, ...]:
        """Scaled so no single feature dominates the k-NN distance.

        n_tests spans 2 to 1,100 and prompt_chars 130 to 4,000; unscaled, the
        distance would be almost entirely prompt length, which is not what the
        pass rates say matters.
        """
        return (self.rank / 4.0,
                min(self.n_tests, 1200) / 1200.0,
                min(self.prompt_chars, 4000) / 4000.0)


def load_problems(conn, problem_ids: list[str]) -> dict[str, Problem]:
    if not problem_ids:
        return {}
    marks = ",".join("?" * len(problem_ids))
    rows = conn.execute(f"""
        SELECT problem_id, COALESCE(difficulty, benchmark) AS tier,
               n_tests, prompt_chars
        FROM problems WHERE problem_id IN ({marks})
    """, problem_ids).fetchall()
    return {r["problem_id"]: Problem(r["problem_id"], r["tier"],
                                     r["n_tests"], r["prompt_chars"])
            for r in rows}


def outcome_grid(conn, config_ids: list[int],
                 problem_ids: list[str]) -> dict[str, dict[int, dict]]:
    """{problem_id: {config_id: {'solved', 'cost'}}} -- the table itself."""
    marks_c = ",".join("?" * len(config_ids))
    marks_p = ",".join("?" * len(problem_ids))
    # Reuses analysis._WASTED rather than restating it. It had been duplicated
    # here, which is how two definitions of "did this cell solve the problem"
    # drift apart -- and the router's routing LABEL is derived from this column,
    # so a divergence would silently mean the router and the frontier were
    # scored against different ground truth.
    rows = conn.execute(f"""
        SELECT g.problem_id, g.config_id,
               COALESCE(g.cost_actual_usd, g.cost_computed_usd) AS cost,
               CASE WHEN {analysis._WASTED} THEN 0
                    ELSE COALESCE(r.passed, 0) END AS solved
        FROM generations g
        JOIN results r ON r.gen_id = g.gen_id
        WHERE COALESCE(g.is_mock, 0) = 0
          AND g.config_id IN ({marks_c}) AND g.problem_id IN ({marks_p})
    """, [*config_ids, *problem_ids]).fetchall()

    grid: dict[str, dict[int, dict]] = {}
    for r in rows:
        grid.setdefault(r["problem_id"], {})[r["config_id"]] = {
            "solved": int(r["solved"]), "cost": r["cost"] or 0.0}
    return grid


def cheapest_solving(cell: dict[int, dict]) -> int | None:
    """The routing label: cheapest config that actually solved this problem."""
    winners = [(v["cost"], cid) for cid, v in cell.items() if v["solved"]]
    return min(winners)[1] if winners else None


# ------------------------------------------------------------------- routers
#
# Each takes (problem, training set, grid) and returns a config_id. Training
# data is only ever the OTHER problems -- never the one being predicted.


def route_always(config_id: int):
    """Always the same config. The degenerate strategy the hull already beats."""
    def router(problem, train, grid):
        return config_id
    return router


def route_by_difficulty(cheap: int, dear: int, threshold: int = 3):
    """A two-line rule: think on hard problems, do not on easy ones.

    Worth measuring precisely because it is what a practitioner would guess
    from the pass-rate table, and it costs nothing to implement.
    """
    def router(problem, train, grid):
        return dear if problem.rank >= threshold else cheap
    return router


def route_knn(k: int = 5):
    """k-NN over free features, predicting the cheapest config that solves.

    Cover & Hart (1967) bounds k-NN's error at twice Bayes error, which is the
    reason to use it rather than something fancier on 60 problems: it is the
    simplest estimator with a known guarantee, and section 10.2 asks that this
    be cited rather than dressed up as new.
    """
    def router(problem, train, grid):
        target = problem.features()
        scored = []
        for other in train:
            label = cheapest_solving(grid.get(other.problem_id, {}))
            if label is None:
                continue      # nothing solved it: no label to learn from
            d = sum((a - b) ** 2 for a, b in zip(target, other.features()))
            scored.append((d, label))
        if not scored:
            return None
        scored.sort(key=lambda x: x[0])
        votes: dict[int, int] = {}
        for _, label in scored[:k]:
            votes[label] = votes.get(label, 0) + 1
        return max(votes.items(), key=lambda kv: (kv[1], -kv[0]))[0]
    return router


# ---------------------------------------------------------------- evaluation


def evaluate(conn, router, config_ids: list[int], problem_ids: list[str],
             *, fallback: int) -> dict:
    """Leave-one-out CV. Returns accuracy and mean cost per problem.

    LOO rather than a single split: with ~60 problems, one split measures the
    split. `fallback` is used when the router declines to choose, so a router
    is never rewarded for abstaining.
    """
    grid = outcome_grid(conn, config_ids, problem_ids)
    probs = load_problems(conn, problem_ids)
    usable = [p for pid, p in probs.items() if pid in grid]

    solved = 0
    cost = 0.0
    picks: dict[int, int] = {}
    for held_out in usable:
        train = [p for p in usable if p.problem_id != held_out.problem_id]
        choice = router(held_out, train, grid) or fallback
        cell = grid[held_out.problem_id].get(choice)
        if cell is None:                       # config not measured here
            choice = fallback
            cell = grid[held_out.problem_id].get(choice)
        if cell is None:
            continue
        picks[choice] = picks.get(choice, 0) + 1
        solved += cell["solved"]
        cost += cell["cost"]

    n = len(usable)
    return {"n": n,
            "accuracy": 100.0 * solved / n if n else 0.0,
            "cost": cost / n if n else 0.0,
            "picks": picks,
            "distinct_configs_used": len(picks)}


def feature_ceiling(conn, config_ids: list[int], problem_ids: list[str]) -> dict:
    """The best any router using ONLY these features could do.

    Group problems by their feature bucket and give each bucket its single best
    config, chosen with full knowledge of the answers. Nothing that reads only
    these features can beat this, so the distance from here to the oracle is
    exactly what the features fail to capture -- not what the estimator got
    wrong.
    """
    grid = outcome_grid(conn, config_ids, problem_ids)
    probs = load_problems(conn, problem_ids)

    buckets: dict[tuple, list[str]] = {}
    for pid, p in probs.items():
        if pid in grid:
            # Coarsen: raw features would give every problem its own bucket and
            # trivially reproduce the oracle, which would measure nothing.
            key = (p.rank, min(p.n_tests, 1200) // 300, p.prompt_chars // 600)
            buckets.setdefault(key, []).append(pid)

    solved = 0
    cost = 0.0
    n = sum(len(v) for v in buckets.values())
    for pids in buckets.values():
        best = None
        for cid in config_ids:
            cells = [grid[pid].get(cid) for pid in pids]
            if any(c is None for c in cells):
                continue
            s = sum(c["solved"] for c in cells)
            c_ = sum(c["cost"] for c in cells)
            if best is None or (s, -c_) > (best[0], -best[1]):
                best = (s, c_)
        if best:
            solved += best[0]
            cost += best[1]
    return {"n": n, "accuracy": 100.0 * solved / n if n else 0.0,
            "cost": cost / n if n else 0.0, "buckets": len(buckets),
            # A ceiling FITTED on the same data it describes: with ~60 problems
            # in ~12 buckets it is 5 problems per bucket, so it is an optimistic
            # upper bound, not a validated score. Read it as "the features are
            # at least this informative", never as an achievable target.
            "problems_per_bucket": n / max(1, len(buckets))}


def decompose_gap(conn, config_ids: list[int], problem_ids: list[str],
                  *, k: int = 5) -> dict:
    """Split the router-to-oracle gap into its causes (section 10.2).

        oracle          per-problem best -- unreachable, needs the answers
        feature ceiling best possible from these features alone
        router          what k-NN actually achieves
        hull            the honest problem-blind baseline

    feature insufficiency = oracle - feature ceiling   (better features needed)
    estimation error      = feature ceiling - router   (better estimator needed)

    The split matters because it says which direction is worth work. A negative
    result that cannot distinguish "my features are too weak" from "my method is
    too weak" is not diagnostic, and section 10.2 asks for exactly that
    distinction.
    """
    orc = analysis.oracle(conn, config_ids, problem_ids)
    ceiling = feature_ceiling(conn, config_ids, problem_ids)

    grid = outcome_grid(conn, config_ids, problem_ids)
    costs = {cid: sum(g[cid]["cost"] for g in grid.values() if cid in g)
             for cid in config_ids}
    cheapest = min(costs, key=costs.get)
    knn = evaluate(conn, route_knn(k), config_ids, problem_ids, fallback=cheapest)

    pts = analysis.frontier(conn, config_ids, problem_ids, n_resamples=0)
    hull = analysis.upper_hull(analysis.pareto_front(pts))
    hull_acc = analysis.hull_accuracy_at(hull, knn["cost"])

    return {
        "oracle": orc,
        "feature_ceiling": ceiling,
        "router": knn,
        "hull_at_router_cost": hull_acc,
        "feature_insufficiency": orc["accuracy"] - ceiling["accuracy"],
        "estimation_error": ceiling["accuracy"] - knn["accuracy"],
        "router_minus_hull": (knn["accuracy"] - hull_acc
                              if hull_acc is not None else None),
    }
